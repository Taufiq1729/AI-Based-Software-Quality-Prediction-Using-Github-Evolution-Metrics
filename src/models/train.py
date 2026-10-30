"""
Model Training Pipeline.
Trains:
1. Logistic Regression (class_weight='balanced')
2. Decision Tree (class_weight='balanced')
3. Random Forest (with GridSearchCV hyperparameter tuning over n_estimators and max_depth)

Evaluates:
- Static-only features (12 features)
- Combined features (15 features: 12 static + 3 Git evolution)

Temporal Validity:
- Strictly trained on chronological training releases (JUnit 4.8, 4.9, 4.11).
- Cross-validation uses TimeSeriesSplit to respect temporal sequence without leakage.
- No testing release data is ever seen or used during training or tuning.
"""

import os
import sys
import logging
from typing import Dict, Any
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
import joblib

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data.feature_extractor import STATIC_FEATURES, FEATURE_COLUMNS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def make_release_time_splits(release_groups: pd.Series) -> list:
    """Create expanding-window CV folds that hold out one whole release each."""
    groups = pd.Series(release_groups).reset_index(drop=True)
    if groups.empty or groups.isna().any():
        raise ValueError("Release groups must be non-empty and contain no missing values.")

    release_order = groups.drop_duplicates().tolist()
    if len(release_order) < 2:
        raise ValueError("At least two releases are required for release-based cross-validation.")

    release_blocks = groups.ne(groups.shift()).cumsum()
    if groups.groupby(release_blocks).first().duplicated().any():
        raise ValueError("Rows for each release must be contiguous and in chronological order.")

    splits = []
    for validation_position in range(1, len(release_order)):
        validation_release = release_order[validation_position]
        train_mask = groups.isin(release_order[:validation_position]).to_numpy()
        validation_mask = groups.eq(validation_release).to_numpy()
        splits.append((np.flatnonzero(train_mask), np.flatnonzero(validation_mask)))
    return splits


def train_models(processed_dir: str = "data/processed",
                 models_dir: str = "src/models/saved") -> Dict[str, Any]:
    os.makedirs(models_dir, exist_ok=True)

    logger.info("Loading preprocessed chronological training data...")
    X_train = pd.read_csv(os.path.join(processed_dir, "X_train.csv"))
    y_train = pd.read_csv(os.path.join(processed_dir, "y_train.csv")).values.ravel()

    assert list(X_train.columns) == FEATURE_COLUMNS, (
        f"X_train columns do not match FEATURE_COLUMNS: {X_train.columns}"
    )

    X_train_static = X_train[STATIC_FEATURES]
    X_train_combined = X_train[FEATURE_COLUMNS]

    logger.info(f"Static features ({len(STATIC_FEATURES)}): {STATIC_FEATURES}")
    logger.info(f"Combined features ({len(FEATURE_COLUMNS)}): {FEATURE_COLUMNS}")
    logger.info(f"Training dataset size: {len(X_train)} samples, Positive defects: {int(y_train.sum())} ({y_train.mean()*100:.2f}%)")

    release_groups_path = os.path.join(processed_dir, "train_release_groups.csv")
    release_groups = pd.read_csv(release_groups_path)["release_commit"]
    if len(release_groups) != len(X_train):
        raise ValueError("Training release-group manifest length does not match X_train.")
    cv = make_release_time_splits(release_groups)

    rf_params = {
        'n_estimators': [50, 100, 150],
        'max_depth': [None, 10, 20],
        'min_samples_split': [2, 5]
    }

    model_configs = {
        'LogisticRegression': (
            LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced'),
            None
        ),
        'DecisionTree': (
            DecisionTreeClassifier(random_state=42, class_weight='balanced'),
            None
        ),
        'RandomForest': (
            RandomForestClassifier(random_state=42, class_weight='balanced'),
            rf_params
        )
    }

    trained_models = {}

    for name, (base_model, params) in model_configs.items():
        logger.info(f"=== Training {name} ===")
        trained_models[name] = {}

        # 1. Static Only (12 features)
        logger.info(f"Fitting {name} (Static Only, 12 features)...")
        if params:
            gs_static = GridSearchCV(base_model, params, cv=cv, scoring='roc_auc', n_jobs=-1)
            gs_static.fit(X_train_static, y_train)
            best_static = gs_static.best_estimator_
            logger.info(f"Best {name} (Static) Params: {gs_static.best_params_}, Best CV ROC-AUC: {gs_static.best_score_:.4f}")
            joblib.dump(best_static, os.path.join(models_dir, f"{name}_static.pkl"))
            trained_models[name]["static"] = best_static
        else:
            base_model.fit(X_train_static, y_train)
            joblib.dump(base_model, os.path.join(models_dir, f"{name}_static.pkl"))
            trained_models[name]["static"] = base_model

        # 2. Combined (15 features: Static + Evolution)
        logger.info(f"Fitting {name} (Combined, 15 features)...")
        if params:
            model_combined_base = type(base_model)(random_state=42, class_weight='balanced')
            gs_combined = GridSearchCV(model_combined_base, params, cv=cv, scoring='roc_auc', n_jobs=-1)
            gs_combined.fit(X_train_combined, y_train)
            best_combined = gs_combined.best_estimator_
            logger.info(f"Best {name} (Combined) Params: {gs_combined.best_params_}, Best CV ROC-AUC: {gs_combined.best_score_:.4f}")
            joblib.dump(best_combined, os.path.join(models_dir, f"{name}_combined.pkl"))
            trained_models[name]["combined"] = best_combined
        else:
            model_combined = type(base_model)(**base_model.get_params())
            model_combined.fit(X_train_combined, y_train)
            joblib.dump(model_combined, os.path.join(models_dir, f"{name}_combined.pkl"))
            trained_models[name]["combined"] = model_combined

    logger.info(f"All fresh models trained successfully and saved to {models_dir}")
    return trained_models


if __name__ == "__main__":
    train_models()
