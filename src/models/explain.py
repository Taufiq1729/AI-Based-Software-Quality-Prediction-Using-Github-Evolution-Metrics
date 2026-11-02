"""Generate Logistic Regression Combined coefficient and SHAP artifacts."""

import hashlib
import json
import logging
import os
import sys
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data.feature_extractor import FEATURE_COLUMNS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MODEL_FILENAME = "LogisticRegression_combined.pkl"
IMPORTANCE_FILENAME = "logistic_regression_combined_feature_coefficients.csv"
SHAP_VALUES_FILENAME = "logistic_regression_combined_shap_values.npy"
SHAP_BASE_VALUES_FILENAME = "logistic_regression_combined_shap_base_values.npy"
SHAP_SAMPLE_FILENAME = "logistic_regression_combined_shap_X_sample.csv"
SHAP_BACKGROUND_FILENAME = "logistic_regression_combined_shap_background.csv"
SHAP_METADATA_FILENAME = "logistic_regression_combined_explanation_metadata.json"
RANDOM_STATE = 42
SHAP_SAMPLE_SIZE = 100
SHAP_BACKGROUND_SIZE = 100
ADDITIVITY_TOLERANCE = 1e-8


def _read_scaled_features(processed_dir: str, filename: str) -> pd.DataFrame:
    path = os.path.join(processed_dir, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Processed feature data not found: {path}")

    features = pd.read_csv(path)
    if list(features.columns) != FEATURE_COLUMNS:
        raise ValueError(f"{filename} feature order differs from FEATURE_COLUMNS.")
    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValueError(f"{filename} contains missing or non-finite feature values.")
    return features


def _validate_scaler(scaler: Any) -> None:
    scaler_features = list(getattr(scaler, "feature_names_in_", []))
    if scaler_features and scaler_features != FEATURE_COLUMNS:
        raise ValueError("Saved scaler feature order differs from FEATURE_COLUMNS.")
    if getattr(scaler, "n_features_in_", len(FEATURE_COLUMNS)) != len(FEATURE_COLUMNS):
        raise ValueError("Saved scaler does not match the 15-feature schema.")


def _positive_class_shap_values(
    shap_output: Any,
    expected_value: Any,
    positive_class_index: int,
    sample_count: int,
) -> tuple[np.ndarray, float]:
    if isinstance(shap_output, list):
        if positive_class_index >= len(shap_output):
            raise ValueError("SHAP output does not contain the positive class.")
        values = np.asarray(shap_output[positive_class_index])
    else:
        values = np.asarray(getattr(shap_output, "values", shap_output))
        if values.ndim == 3:
            values = values[:, :, positive_class_index]

    expected = np.asarray(expected_value)
    if expected.ndim > 0:
        if positive_class_index >= expected.size:
            raise ValueError("SHAP base values do not contain the positive class.")
        expected = expected.reshape(-1)[positive_class_index]

    if values.shape != (sample_count, len(FEATURE_COLUMNS)):
        raise ValueError(f"Unexpected positive-class SHAP shape: {values.shape}")
    base_value = float(expected)
    if not np.isfinite(values).all() or not np.isfinite(base_value):
        raise ValueError("SHAP values or base value contain non-finite values.")
    return values, base_value


def generate_explanations(
    processed_dir: str = "data/processed",
    models_dir: str = "src/models/saved",
    results_dir: str = "data/results",
) -> dict[str, Any]:
    """Generate reproducible explanations for the deployed model's scaled inputs."""
    model_path = os.path.join(models_dir, MODEL_FILENAME)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Logistic Regression Combined model not found: {model_path}")

    scaler_path = os.path.join(processed_dir, "scaler.pkl")
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Saved training scaler not found: {scaler_path}")

    model = joblib.load(model_path)
    if list(getattr(model, "feature_names_in_", [])) != FEATURE_COLUMNS:
        raise ValueError("Saved model feature order differs from FEATURE_COLUMNS.")
    if getattr(model, "n_features_in_", None) != len(FEATURE_COLUMNS):
        raise ValueError("Saved model does not accept exactly 15 features.")

    classes = list(model.classes_)
    if len(classes) != 2 or 1 not in classes:
        raise ValueError(f"Expected a binary classifier with defective class 1; found {classes}.")
    positive_class_index = classes.index(1)
    if model.coef_.shape != (1, len(FEATURE_COLUMNS)):
        raise ValueError(f"Unexpected Logistic Regression coefficient shape: {model.coef_.shape}")

    X_train = _read_scaled_features(processed_dir, "X_train.csv")
    X_test = _read_scaled_features(processed_dir, "X_test.csv")
    scaler = joblib.load(scaler_path)
    _validate_scaler(scaler)

    sample_size = min(SHAP_SAMPLE_SIZE, len(X_test))
    background_size = min(SHAP_BACKGROUND_SIZE, len(X_train))
    if not sample_size or not background_size:
        raise ValueError("Training and test feature data must both contain at least one row.")

    X_sample = X_test.sample(n=sample_size, random_state=RANDOM_STATE)
    background = X_train.sample(n=background_size, random_state=RANDOM_STATE)

    import shap
    from scipy.special import expit

    explainer = shap.LinearExplainer(model, background)
    raw_shap_values = explainer.shap_values(X_sample)
    shap_values, base_value = _positive_class_shap_values(
        raw_shap_values,
        explainer.expected_value,
        positive_class_index,
        sample_size,
    )

    decision_scores = np.asarray(model.decision_function(X_sample)).reshape(-1)
    reconstructed_scores = base_value + shap_values.sum(axis=1)
    additivity_error = float(np.max(np.abs(reconstructed_scores - decision_scores)))
    positive_probabilities = model.predict_proba(X_sample)[:, positive_class_index]
    reconstructed_probabilities = expit(reconstructed_scores)
    probability_error = float(np.max(np.abs(reconstructed_probabilities - positive_probabilities)))
    if not np.allclose(
        reconstructed_scores,
        decision_scores,
        rtol=ADDITIVITY_TOLERANCE,
        atol=ADDITIVITY_TOLERANCE,
    ):
        raise ValueError(f"SHAP additivity failed in log-odds space: max error {additivity_error}")
    if not np.allclose(
        reconstructed_probabilities,
        positive_probabilities,
        rtol=ADDITIVITY_TOLERANCE,
        atol=ADDITIVITY_TOLERANCE,
    ):
        raise ValueError(
            "SHAP-derived positive-class probabilities do not match model.predict_proba: "
            f"max error {probability_error}"
        )

    coefficients = model.coef_[0]
    importance = pd.DataFrame({
        "Feature": FEATURE_COLUMNS,
        "Signed_Coefficient": coefficients,
        "Absolute_Coefficient": np.abs(coefficients),
    })

    os.makedirs(results_dir, exist_ok=True)
    importance.to_csv(os.path.join(results_dir, IMPORTANCE_FILENAME), index=False)
    np.save(os.path.join(results_dir, SHAP_VALUES_FILENAME), shap_values)
    np.save(os.path.join(results_dir, SHAP_BASE_VALUES_FILENAME), np.asarray(base_value))
    X_sample.to_csv(os.path.join(results_dir, SHAP_SAMPLE_FILENAME), index=False)
    background.to_csv(os.path.join(results_dir, SHAP_BACKGROUND_FILENAME), index=False)

    model_digest = hashlib.sha256()
    with open(model_path, "rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            model_digest.update(chunk)

    metadata = {
        "model_file": MODEL_FILENAME,
        "model_sha256": model_digest.hexdigest(),
        "model_class": f"{type(model).__module__}.{type(model).__name__}",
        "feature_columns": FEATURE_COLUMNS,
        "positive_class": 1,
        "positive_class_index": positive_class_index,
        "shap_output_space": "Logistic Regression decision_function (log-odds for class 1)",
        "input_representation": (
            "The API accepts raw ordered FEATURE_COLUMNS and transforms them with the saved "
            "training StandardScaler before model inference. SHAP backgrounds and samples are "
            "the standardized X_train.csv and X_test.csv rows passed directly to the model."
        ),
        "scaler_file": "scaler.pkl",
        "shap_explainer": "shap.LinearExplainer",
        "shap_version": shap.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "scikit_learn_version": sklearn.__version__,
        "random_state": RANDOM_STATE,
        "background_sample_count": background_size,
        "explained_sample_count": sample_size,
        "base_value": base_value,
        "validation": {
            "model_feature_order_matches_FEATURE_COLUMNS": True,
            "sample_and_background_are_finite_and_ordered": True,
            "positive_class_is_defective_class_1": True,
            "maximum_log_odds_additivity_error": additivity_error,
            "maximum_probability_reconstruction_error": probability_error,
            "tolerance": ADDITIVITY_TOLERANCE,
        },
    }
    with open(os.path.join(results_dir, SHAP_METADATA_FILENAME), "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    logger.info("Generated Logistic Regression Combined explanations in %s", results_dir)
    logger.info("Maximum SHAP log-odds additivity error: %.3g", additivity_error)
    logger.info("Maximum positive-class probability reconstruction error: %.3g", probability_error)
    return metadata


if __name__ == "__main__":
    generate_explanations()
