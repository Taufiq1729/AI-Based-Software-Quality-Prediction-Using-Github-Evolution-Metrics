"""
Model Evaluation Pipeline.
Evaluates all trained models on the held-out test set:
- Accuracy
- Precision
- Recall
- F1-Score
- ROC-AUC
- Confusion Matrix
- ROC Curve
- Precision-Recall Curve
Saves fresh, un-fabricated evaluation results to data/results/evaluation_metrics.json.
"""

import os
import sys
import json
import numpy as np
import logging
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    auc,
    confusion_matrix,
    roc_curve,
    precision_recall_curve
)
import joblib

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data.feature_extractor import STATIC_FEATURES, FEATURE_COLUMNS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _evaluate_predictions(y_true, y_pred, y_prob) -> dict:
    positive_count = int((y_true == 1).sum())
    both_classes_present = len(set(y_true.tolist())) == 2
    if positive_count:
        precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_prob)
        trap_pr_auc = float(auc(recall_curve, precision_curve))
        pr_curve = {"precision": precision_curve.tolist(), "recall": recall_curve.tolist()}
    else:
        trap_pr_auc = None
        pr_curve = None
    average_precision = float(average_precision_score(y_true, y_prob)) if positive_count else None

    positive_scores = y_prob[y_true == 1]
    negative_scores = y_prob[y_true == 0]
    quantiles = [0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0]

    def score_quantiles(values):
        return ({str(q): float(np.quantile(values, q)) for q in quantiles}
                if len(values) else None)

    return {
        "Accuracy": float(accuracy_score(y_true, y_pred)),
        "Balanced_Accuracy": float(balanced_accuracy_score(y_true, y_pred)) if both_classes_present else None,
        "Precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "Recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "F1_Score": float(f1_score(y_true, y_pred, zero_division=0)),
        "ROC_AUC": float(roc_auc_score(y_true, y_prob)) if both_classes_present else None,
        "PR_AUC": average_precision,
        "Average_Precision": average_precision,
        "PR_AUC_trapezoidal": trap_pr_auc,
        "ConfusionMatrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "ROC_Curve": None,
        "PR_Curve": pr_curve,
        "Sample_Count": int(len(y_true)),
        "Defective_Support": positive_count,
        "NonDefective_Support": int((y_true == 0).sum()),
        "Predicted_Positive_Count": int((y_pred == 1).sum()),
        "Positive_Score_Summary": score_quantiles(positive_scores),
        "NonPositive_Score_Summary": score_quantiles(negative_scores),
    }


def evaluate_models(processed_dir: str = "data/processed",
                    models_dir: str = "src/models/saved",
                    results_dir: str = "data/results") -> dict:
    os.makedirs(results_dir, exist_ok=True)

    logger.info("Loading held-out test data...")
    X_test = pd.read_csv(os.path.join(processed_dir, "X_test.csv"))
    y_test = pd.read_csv(os.path.join(processed_dir, "y_test.csv")).values.ravel()
    y_test = y_test.astype(int)
    release_manifest = pd.read_csv(os.path.join(processed_dir, "test_release_groups.csv"))
    if len(release_manifest) != len(y_test):
        raise ValueError("Test release manifest length does not match y_test.")
    release_column = "release_commit" if "release_commit" in release_manifest else release_manifest.columns[0]
    release_groups = release_manifest[release_column].astype(str)

    assert list(X_test.columns) == FEATURE_COLUMNS, f"X_test columns mismatch: {X_test.columns}"

    X_test_static = X_test[STATIC_FEATURES]
    X_test_combined = X_test[FEATURE_COLUMNS]

    models = ['LogisticRegression', 'DecisionTree', 'RandomForest']
    results = {"_metadata": {
        "primary_PR_AUC": "Average_Precision (sklearn average_precision_score)",
        "PR_AUC_trapezoidal": "Separate trapezoidal auc(recall, precision); not used as the primary PR ranking metric.",
        "threshold_selection": "No threshold was selected on the held-out test set; classifiers use their default predict() rule.",
        "prediction_probability_threshold": 0.5,
    }}
    per_release = {}
    model_predictions = {}

    for name in models:
        results[name] = {}
        for feature_set, X in [("static", X_test_static), ("combined", X_test_combined)]:
            model_path = os.path.join(models_dir, f"{name}_{feature_set}.pkl")
            if not os.path.exists(model_path):
                logger.warning(f"Model not found: {model_path}")
                continue

            model = joblib.load(model_path)
            y_pred = model.predict(X)
            if hasattr(model, "predict_proba"):
                class_index = list(model.classes_).index(1)
                y_prob = model.predict_proba(X)[:, class_index]
            else:
                y_prob = y_pred.astype(float)
            model_predictions[(name, feature_set)] = (y_pred.astype(int), y_prob)
            metrics = _evaluate_predictions(y_test, y_pred, y_prob)

            logger.info(
                f"[{name} - {feature_set}] Acc: {metrics['Accuracy']:.4f} | "
                f"Balanced Acc: {metrics['Balanced_Accuracy']:.4f} | "
                f"Prec: {metrics['Precision']:.4f} | Rec: {metrics['Recall']:.4f} | "
                f"F1: {metrics['F1_Score']:.4f} | ROC-AUC: {metrics['ROC_AUC']:.4f} | "
                f"AP: {metrics['PR_AUC']:.4f} | Trap PR-AUC: {metrics['PR_AUC_trapezoidal']:.4f}"
            )
            fpr, tpr, _ = roc_curve(y_test, y_prob)
            metrics["ROC_Curve"] = {"fpr": fpr.tolist(), "tpr": tpr.tolist()}
            results.setdefault(name, {})[feature_set] = metrics

    baseline_prediction = np.zeros_like(y_test, dtype=int)
    baseline_probability = np.zeros(len(y_test), dtype=float)
    results["MajorityClassBaseline"] = {
        "none": _evaluate_predictions(y_test, baseline_prediction, baseline_probability)
    }
    model_predictions[("MajorityClassBaseline", "none")] = (baseline_prediction, baseline_probability)

    for release in release_groups.drop_duplicates():
        mask = release_groups.eq(release).to_numpy()
        release_labels = y_test[mask]
        release_results = {
            "Sample_Count": int(mask.sum()),
            "Defective_Support": int((release_labels == 1).sum()),
            "NonDefective_Support": int((release_labels == 0).sum()),
            "models": {},
        }
        for key, (predictions, probabilities) in model_predictions.items():
            model_name, feature_set = key
            release_results["models"].setdefault(model_name, {})[feature_set] = _evaluate_predictions(
                release_labels, predictions[mask], probabilities[mask]
            )
        per_release[str(release)] = release_results
    results["PerRelease"] = per_release

    output_path = os.path.join(results_dir, "evaluation_metrics.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=4)

    logger.info(f"Evaluation complete. Fresh results saved to {output_path}")
    return results


if __name__ == "__main__":
    evaluate_models()
