"""
Authoritative Data Preprocessing Pipeline.
Implements:
1. Chronological, release-aware train/test splitting (No temporal data leakage).
   - Training Releases (2009 - 2012):
     * JUnit 4.8  (commit 5a3a326096cf65a58272ee89a5ef1c164cfd9d33)
     * JUnit 4.9  (commit 61f06547599bb6b98bca99d5bc457eb20bc17cab)
     * JUnit 4.11 (commit 88c28a42a6fb7dc462c4bc504189a76a815fc265)
   - Testing Releases (2014 - 2020):
     * JUnit 4.12   (commit 64155f8a9babcfcf4263cf4d08253a1556e75481)
     * JUnit 4.13.1 (commit 1b683f4ec07bcfa40149f086d32240f805487e66)
2. Imputation medians computed strictly on training releases.
3. StandardScaler fitted strictly on training releases.
4. Test set transformed without data leakage.
5. Persists reproducible datasets, imputer medians, and scaler to data/processed/.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import joblib

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data.feature_extractor import FEATURE_COLUMNS, STATIC_FEATURES, EVOLUTION_FEATURES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Proposed and audited chronological release split
TRAIN_RELEASE_COMMITS = [
    "5a3a326096cf65a58272ee89a5ef1c164cfd9d33",  # JUnit 4.8  (2009-11-30)
    "61f06547599bb6b98bca99d5bc457eb20bc17cab",  # JUnit 4.9  (2011-08-22)
    "88c28a42a6fb7dc462c4bc504189a76a815fc265",  # JUnit 4.11 (2012-10-15)
]

TEST_RELEASE_COMMITS = [
    "64155f8a9babcfcf4263cf4d08253a1556e75481",  # JUnit 4.12   (2014-12-04)
    "1b683f4ec07bcfa40149f086d32240f805487e66",  # JUnit 4.13.1 (2020-10-11)
]


def load_regenerated_releases(
    derived_dir: str = "data/derived/junit4_regenerated",
    release_commits: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Loads regenerated release CSVs for the specified release commits.
    """
    derived_path = Path(derived_dir).resolve()
    dfs = []
    for commit in release_commits:
        fname = f"dataset-{commit}.csv"
        fpath = os.path.join(derived_dir, fname)
        if not os.path.exists(fpath):
            raise FileNotFoundError(
                f"Regenerated release dataset not found: {fpath}. "
                f"Run rebuild_static_metrics.py first."
            )
        df = pd.read_csv(fpath)
        df["release_commit"] = commit
        dfs.append(df)
        defects = int(df["isDefective"].sum())
        logger.info(f"Loaded release {commit[:10]}: {len(df)} records, {defects} defects ({defects/len(df)*100:.2f}%)")

    combined = pd.concat(dfs, ignore_index=True)
    return combined


def preprocess_data(
    derived_dir: str = "data/derived/junit4_regenerated",
    processed_dir: str = "data/processed",
    train_commits: Optional[List[str]] = None,
    test_commits: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Full leak-free chronological preprocessing pipeline:
    1. Loads regenerated datasets for train releases and test releases.
    2. Validates all 15 FEATURE_COLUMNS exist.
    3. Computes imputation medians strictly on training set.
    4. Fits StandardScaler strictly on training set.
    5. Transforms test set using training parameters.
    6. Saves processed datasets, imputer medians, and scaler to processed_dir.
    """
    os.makedirs(processed_dir, exist_ok=True)
    train_commits = train_commits or TRAIN_RELEASE_COMMITS
    test_commits = test_commits or TEST_RELEASE_COMMITS

    logger.info("=== Loading Training Releases (Chronological) ===")
    df_train = load_regenerated_releases(derived_dir, train_commits)

    logger.info("=== Loading Testing Releases (Chronological) ===")
    df_test = load_regenerated_releases(derived_dir, test_commits)

    # Validate feature presence
    for col in FEATURE_COLUMNS + ["isDefective"]:
        if col not in df_train.columns:
            raise KeyError(f"Missing required column in training data: {col}")
        if col not in df_test.columns:
            raise KeyError(f"Missing required column in test data: {col}")

    X_train = df_train[FEATURE_COLUMNS].copy()
    y_train = df_train["isDefective"].fillna(0).astype(int)

    X_test = df_test[FEATURE_COLUMNS].copy()
    y_test = df_test["isDefective"].fillna(0).astype(int)

    train_defects = int(y_train.sum())
    test_defects = int(y_test.sum())

    logger.info(
        f"Train set: {len(X_train)} samples across {len(train_commits)} releases | "
        f"Defective: {train_defects} ({train_defects/len(X_train)*100:.2f}%)"
    )
    logger.info(
        f"Test set:  {len(X_test)} samples across {len(test_commits)} releases | "
        f"Defective: {test_defects} ({test_defects/len(X_test)*100:.2f}%)"
    )

    # 1. Imputation medians computed strictly on X_train (No Data Leakage)
    train_medians = X_train.median().to_dict()
    medians_path = os.path.join(processed_dir, "imputer_medians.json")
    with open(medians_path, "w") as f:
        json.dump(train_medians, f, indent=4)

    X_train = X_train.fillna(train_medians)
    X_test = X_test.fillna(train_medians)

    # 2. Fit StandardScaler strictly on X_train (No Data Leakage)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    X_train_df = pd.DataFrame(X_train_scaled, columns=FEATURE_COLUMNS)
    X_test_df = pd.DataFrame(X_test_scaled, columns=FEATURE_COLUMNS)

    # 3. Save processed artifacts
    X_train_df.to_csv(os.path.join(processed_dir, "X_train.csv"), index=False)
    X_test_df.to_csv(os.path.join(processed_dir, "X_test.csv"), index=False)
    y_train.to_csv(os.path.join(processed_dir, "y_train.csv"), index=False)
    y_test.to_csv(os.path.join(processed_dir, "y_test.csv"), index=False)

    # Save release manifests for time-aware cross-validation
    df_train[["release_commit"]].to_csv(os.path.join(processed_dir, "train_release_groups.csv"), index=False)
    df_test[["release_commit"]].to_csv(os.path.join(processed_dir, "test_release_groups.csv"), index=False)

    scaler_path = os.path.join(processed_dir, "scaler.pkl")
    joblib.dump(scaler, scaler_path)
    logger.info(f"Preprocessing complete. Processed datasets and scaler saved to {processed_dir}")

    return X_train_df, X_test_df, y_train, y_test


if __name__ == "__main__":
    preprocess_data()
