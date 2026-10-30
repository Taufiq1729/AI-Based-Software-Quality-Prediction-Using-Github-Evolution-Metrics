"""
Explainability Pipeline.
Extracts:
1. Random Forest feature importance for all 15 real features.
2. SHAP TreeExplainer values and base values for model interpretation.
Persists outputs to data/results/ for the frontend analytics dashboard.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import joblib

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data.feature_extractor import FEATURE_COLUMNS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def generate_explanations(processed_dir: str = "data/processed",
                          models_dir: str = "src/models/saved",
                          results_dir: str = "data/results") -> None:
    os.makedirs(results_dir, exist_ok=True)

    logger.info("Loading test data...")
    X_test = pd.read_csv(os.path.join(processed_dir, "X_test.csv"))
    assert list(X_test.columns) == FEATURE_COLUMNS, f"X_test columns mismatch: {X_test.columns}"

    model_path = os.path.join(models_dir, "RandomForest_combined.pkl")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Random Forest combined model not found at {model_path}. Train models first.")

    model = joblib.load(model_path)

    # 1. Feature Importance
    logger.info("Extracting Random Forest feature importances...")
    importances = model.feature_importances_
    feature_importance_df = pd.DataFrame({
        'Feature': FEATURE_COLUMNS,
        'Importance': importances
    }).sort_values(by='Importance', ascending=False)

    importance_out = os.path.join(results_dir, "feature_importance.csv")
    feature_importance_df.to_csv(importance_out, index=False)
    logger.info(f"Top 5 most important features:\n{feature_importance_df.head(5).to_string(index=False)}")

    # 2. SHAP Values
    logger.info("Calculating SHAP values...")
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        # Sample 100 test points for fast and responsive dashboard visualization
        sample_size = min(100, len(X_test))
        X_sample = X_test.sample(n=sample_size, random_state=42)
        raw_shap = explainer.shap_values(X_sample)

        # Handle different SHAP return shapes across library versions
        if isinstance(raw_shap, list):
            # Binary classification: list of [class 0, class 1]
            shap_values_class1 = raw_shap[1]
            expected_val = explainer.expected_value[1] if isinstance(explainer.expected_value, (list, np.ndarray)) else explainer.expected_value
        elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 3:
            # Shape: (N, features, classes) -> extract class 1
            shap_values_class1 = raw_shap[:, :, 1]
            expected_val = explainer.expected_value[1] if isinstance(explainer.expected_value, (list, np.ndarray)) else explainer.expected_value
        else:
            shap_values_class1 = raw_shap
            expected_val = explainer.expected_value

        np.save(os.path.join(results_dir, "shap_values.npy"), np.array(shap_values_class1))
        np.save(os.path.join(results_dir, "shap_base_values.npy"), np.array(expected_val))
        X_sample.to_csv(os.path.join(results_dir, "shap_X_sample.csv"), index=False)
        logger.info(f"SHAP explanations successfully generated and saved to {results_dir}")
    except Exception as e:
        logger.error(f"SHAP explanation generation encountered an issue: {e}", exc_info=True)


if __name__ == "__main__":
    generate_explanations()
