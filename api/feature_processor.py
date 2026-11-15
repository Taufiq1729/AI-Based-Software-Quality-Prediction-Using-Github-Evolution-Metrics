import os
import joblib
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple

STATIC_FEATURES = [
    'LOC', 'WMC', 'DIT', 'NOC', 'RFC', 'LCOM5',
    'CBO', 'NPA', 'NPM', 'NLE', 'CBOI', 'CD'
]

EVOLUTION_FEATURES = [
    'code_churn', 'revision_count', 'developer_count'
]

ALL_FEATURES = STATIC_FEATURES + EVOLUTION_FEATURES

class FeatureProcessor:
    """
    Standardizes and prepares feature sets for ML inference, ensuring exact column
    ordering and scaling identical to the training pipeline.
    """

    def __init__(self, scaler_path: str = "data/processed/scaler.pkl"):
        self.scaler_path = scaler_path
        self.scaler = None
        self._load_scaler()

    def _load_scaler(self):
        global ALL_FEATURES, STATIC_FEATURES
        if os.path.exists(self.scaler_path):
            try:
                self.scaler = joblib.load(self.scaler_path)
                if hasattr(self.scaler, "feature_names_in_"):
                    # Dynamically ensure exact alignment with fitted scaler
                    ALL_FEATURES = list(self.scaler.feature_names_in_)
                    STATIC_FEATURES = [f for f in ALL_FEATURES if f not in EVOLUTION_FEATURES]
            except Exception as e:
                print(f"Warning: Failed to load scaler from {self.scaler_path}: {e}")
        else:
            print(f"Warning: Scaler not found at {self.scaler_path}")

    def prepare_dataframe(self, records: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Converts a list of file metric records into a DataFrame aligned with ALL_FEATURES.
        """
        df = pd.DataFrame(records)
        # Ensure all columns exist
        for col in ALL_FEATURES:
            if col not in df.columns:
                df[col] = 0.0
        
        # Fill any missing values with 0.0
        feature_df = df[ALL_FEATURES].copy().fillna(0.0).astype(float)
        return feature_df

    def transform_combined(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Scales all 15 features using the trained StandardScaler.
        """
        if self.scaler is None:
            raise RuntimeError("StandardScaler is not loaded.")
        
        df_ordered = df_raw[ALL_FEATURES]
        scaled_array = self.scaler.transform(df_ordered)
        return pd.DataFrame(scaled_array, columns=ALL_FEATURES, index=df_raw.index)

    def transform_static(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Scales the 12 static features. Since scaler was fitted on 15 features,
        we transform all 15 features and extract the static columns.
        """
        if self.scaler is None:
            raise RuntimeError("StandardScaler is not loaded.")
        
        df_ordered = df_raw[ALL_FEATURES]
        scaled_array = self.scaler.transform(df_ordered)
        scaled_df = pd.DataFrame(scaled_array, columns=ALL_FEATURES, index=df_raw.index)
        return scaled_df[STATIC_FEATURES]

