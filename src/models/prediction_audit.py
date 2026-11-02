"""Audit inference consistency, probability calibration, and score distribution."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    auc,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data.feature_extractor import FEATURE_COLUMNS
from src.data.preprocessing import TEST_RELEASE_COMMITS, TRAIN_RELEASE_COMMITS, load_regenerated_releases

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MODEL_PATH = Path("src/models/saved/LogisticRegression_combined.pkl")
PROCESSED_DIR = Path("data/processed")
RESULTS_DIR = Path("data/results")
REPOSITORY_SCAN_PATH = Path("data/repository_scan_integration/java_design_patterns_scored_files.csv")
REPOSITORY_METADATA_PATH = Path("data/repository_scan_integration/java_design_patterns_scan_summary.json")
RISK_THRESHOLD = 0.5
PROBABILITY_BINS = np.linspace(0.0, 1.0, 11)
TOP_K_VALUES = (5, 10, 20, 50)
TOP_FILES_FOR_CONTRIBUTIONS = 20


def _json_number(value: Any) -> float | None:
    return float(value) if pd.notna(value) and np.isfinite(value) else None


def _calibration_bins(y_true: np.ndarray, probabilities: np.ndarray) -> tuple[pd.DataFrame, float]:
    bin_indices = np.minimum(np.digitize(probabilities, PROBABILITY_BINS[1:-1]), 9)
    rows = []
    weighted_error = 0.0
    for bin_index in range(10):
        mask = bin_indices == bin_index
        count = int(mask.sum())
        average_probability = float(probabilities[mask].mean()) if count else np.nan
        observed_frequency = float(y_true[mask].mean()) if count else np.nan
        if count:
            weighted_error += count / len(y_true) * abs(average_probability - observed_frequency)
        rows.append({
            "probability_interval": f"{bin_index * 10}-{(bin_index + 1) * 10}%",
            "lower_bound_inclusive": float(PROBABILITY_BINS[bin_index]),
            "upper_bound_exclusive": float(PROBABILITY_BINS[bin_index + 1]),
            "sample_count": count,
            "average_predicted_score": average_probability,
            "observed_defect_fraction": observed_frequency,
        })
    return pd.DataFrame(rows), float(weighted_error)


def _feature_distribution(
    training_raw: pd.DataFrame,
    scanner_raw: pd.DataFrame,
    training_imputed: pd.DataFrame,
    scanner_imputed: pd.DataFrame,
    training_scaled: pd.DataFrame,
    scanner_scaled: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for feature in FEATURE_COLUMNS:
        train_values = training_raw[feature].dropna()
        scanner_values = scanner_raw[feature]
        train_min = float(train_values.min())
        train_max = float(train_values.max())
        rows.append({
            "feature": feature,
            "training_missing_count": int(training_raw[feature].isna().sum()),
            "scanner_missing_count": int(scanner_raw[feature].isna().sum()),
            "training_min": train_min,
            "training_max": train_max,
            "training_mean": float(train_values.mean()),
            "training_median": float(train_values.median()),
            "training_std": float(train_values.std(ddof=1)),
            "training_p01": float(train_values.quantile(0.01)),
            "training_p99": float(train_values.quantile(0.99)),
            "scanner_min": float(scanner_values.min()),
            "scanner_max": float(scanner_values.max()),
            "scanner_mean": float(scanner_values.mean()),
            "scanner_median": float(scanner_values.median()),
            "scanner_std": float(scanner_values.std(ddof=1)),
            "scanner_p01": float(scanner_values.quantile(0.01)),
            "scanner_p99": float(scanner_values.quantile(0.99)),
            "scanner_outside_training_range_count": int(
                ((scanner_values < train_min) | (scanner_values > train_max)).sum()
            ),
            "scanner_outside_training_range_fraction": float(
                ((scanner_values < train_min) | (scanner_values > train_max)).mean()
            ),
            "scanner_missing_count_after_imputation": int(scanner_imputed[feature].isna().sum()),
            "training_imputed_mean": float(training_imputed[feature].mean()),
            "training_imputed_std": float(training_imputed[feature].std(ddof=1)),
            "scanner_scaled_mean": float(scanner_scaled[feature].mean()),
            "scanner_scaled_std": float(scanner_scaled[feature].std(ddof=1)),
            "scanner_scaled_min": float(scanner_scaled[feature].min()),
            "scanner_scaled_max": float(scanner_scaled[feature].max()),
        })
    return pd.DataFrame(rows)


def _feature_contributions(
    scanner_raw: pd.DataFrame,
    scanner_imputed: pd.DataFrame,
    scanner_scaled: pd.DataFrame,
    files: pd.Series,
    scores: np.ndarray,
    model: Any,
    training_raw: pd.DataFrame,
    medians: dict[str, float],
) -> pd.DataFrame:
    order = np.argsort(-scores, kind="stable")[:TOP_FILES_FOR_CONTRIBUTIONS]
    coefficients = model.coef_[0]
    records = []
    for rank, row_index in enumerate(order, start=1):
        for feature_index, feature in enumerate(FEATURE_COLUMNS):
            contribution = float(scanner_scaled.iloc[row_index, feature_index] * coefficients[feature_index])
            train_values = training_raw[feature].dropna()
            raw_value = scanner_raw.iloc[row_index][feature]
            records.append({
                "rank": rank,
                "file": files.iloc[row_index],
                "model_score": float(scores[row_index]),
                "feature": feature,
                "raw_feature_value": _json_number(raw_value),
                "training_median_imputation_value": float(medians[feature]),
                "imputed_feature_value": float(scanner_imputed.iloc[row_index, feature_index]),
                "standardized_feature_value": float(scanner_scaled.iloc[row_index, feature_index]),
                "training_raw_min": float(train_values.min()),
                "training_raw_max": float(train_values.max()),
                "outside_training_raw_range": bool(
                    pd.notna(raw_value)
                    and (raw_value < train_values.min() or raw_value > train_values.max())
                ),
                "coefficient_per_standard_deviation": float(coefficients[feature_index]),
                "log_odds_contribution": contribution,
            })
    return pd.DataFrame(records)


def _plot_calibration(y_true: np.ndarray, probabilities: np.ndarray, output_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    observed, predicted = calibration_curve(
        y_true,
        probabilities,
        n_bins=10,
        strategy="uniform",
        pos_label=1,
    )
    figure, axis = plt.subplots(figsize=(7, 6))
    axis.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect calibration")
    axis.plot(predicted, observed, marker="o", label="Logistic Regression Combined")
    axis.set(
        xlabel="Mean predicted score",
        ylabel="Observed defect fraction",
        title="Reliability on the existing held-out JUnit test set",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    axis.legend()
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def run_prediction_audit(results_dir: str | Path = RESULTS_DIR) -> dict[str, Any]:
    """Reproduce held-out results and diagnose the saved Java Design Patterns scan."""
    output_dir = Path(results_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(PROCESSED_DIR / "scaler.pkl")
    medians = json.loads((PROCESSED_DIR / "imputer_medians.json").read_text(encoding="utf-8"))
    if list(model.feature_names_in_) != FEATURE_COLUMNS or list(medians) != FEATURE_COLUMNS:
        raise ValueError("Model or imputation median ordering differs from FEATURE_COLUMNS.")
    if list(getattr(scaler, "feature_names_in_", [])) != FEATURE_COLUMNS:
        raise ValueError("Saved scaler feature order differs from FEATURE_COLUMNS.")

    train_release_data = load_regenerated_releases(release_commits=TRAIN_RELEASE_COMMITS)
    test_release_data = load_regenerated_releases(release_commits=TEST_RELEASE_COMMITS)
    train_raw = train_release_data[FEATURE_COLUMNS].copy()
    test_raw = test_release_data[FEATURE_COLUMNS].copy()
    train_imputed = train_raw.fillna(medians)
    test_imputed = test_raw.fillna(medians)
    train_scaled = pd.DataFrame(scaler.transform(train_imputed), columns=FEATURE_COLUMNS)
    test_scaled = pd.DataFrame(scaler.transform(test_imputed), columns=FEATURE_COLUMNS)

    stored_train = pd.read_csv(PROCESSED_DIR / "X_train.csv")[FEATURE_COLUMNS]
    stored_test = pd.read_csv(PROCESSED_DIR / "X_test.csv")[FEATURE_COLUMNS]
    y_test = pd.read_csv(PROCESSED_DIR / "y_test.csv").iloc[:, 0].to_numpy(dtype=int)
    if not np.array_equal(test_release_data["isDefective"].to_numpy(dtype=int), y_test):
        raise ValueError("Raw held-out labels do not match the saved held-out labels/order.")
    if not np.allclose(train_scaled, stored_train, atol=1e-10, rtol=1e-10):
        raise ValueError("Reconstructed training transform differs from saved X_train.csv.")
    if not np.allclose(test_scaled, stored_test, atol=1e-10, rtol=1e-10):
        raise ValueError("Reconstructed held-out transform differs from saved X_test.csv.")

    test_probabilities = model.predict_proba(stored_test)[:, list(model.classes_).index(1)]
    test_predictions = model.predict(stored_test).astype(int)
    precision_curve, recall_curve, _ = precision_recall_curve(y_test, test_probabilities)
    prevalence = float(y_test.mean())
    calibration_frame, expected_calibration_error = _calibration_bins(y_test, test_probabilities)
    calibration_frame.to_csv(output_dir / "prediction_audit_calibration_bins.csv", index=False)
    _plot_calibration(
        y_test,
        test_probabilities,
        output_dir / "prediction_audit_reliability_diagram.png",
    )

    ranking_order = np.argsort(-test_probabilities, kind="stable")
    ranking_metrics = {}
    for k in TOP_K_VALUES:
        selected = ranking_order[: min(k, len(ranking_order))]
        top_precision = float(y_test[selected].mean())
        top_recall = float(y_test[selected].sum() / y_test.sum()) if y_test.sum() else None
        ranking_metrics[str(k)] = {
            "sample_count": int(len(selected)),
            "defect_count": int(y_test[selected].sum()),
            "precision_at_k": top_precision,
            "recall_at_k": top_recall,
            "lift_over_test_prevalence": top_precision / prevalence if prevalence else None,
        }

    matrix = confusion_matrix(y_test, test_predictions, labels=[0, 1])
    baseline_brier = float(brier_score_loss(y_test, np.full(len(y_test), prevalence)))
    baseline_log_loss = float(log_loss(y_test, np.full(len(y_test), prevalence), labels=[0, 1]))
    if not np.isfinite(test_probabilities).all() or ((test_probabilities < 0) | (test_probabilities > 1)).any():
        raise ValueError("Held-out model scores must be finite probabilities in [0, 1].")
    model_metrics = {
        "sample_count": int(len(y_test)),
        "defective_count": int(y_test.sum()),
        "defect_prevalence": prevalence,
        "confusion_matrix_tn_fp_fn_tp": matrix.ravel().tolist(),
        "accuracy": float(accuracy_score(y_test, test_predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, test_predictions)),
        "precision": float(precision_score(y_test, test_predictions, zero_division=0)),
        "recall": float(recall_score(y_test, test_predictions, zero_division=0)),
        "f1": float(f1_score(y_test, test_predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, test_probabilities)),
        "average_precision": float(average_precision_score(y_test, test_probabilities)),
        "pr_auc_trapezoidal": float(auc(recall_curve, precision_curve)),
        "brier_score": float(brier_score_loss(y_test, test_probabilities)),
        "log_loss": float(log_loss(y_test, test_probabilities, labels=[0, 1])),
        "expected_calibration_error_10_equal_width_bins": expected_calibration_error,
        "prevalence_only_baseline_brier_score": baseline_brier,
        "prevalence_only_baseline_log_loss": baseline_log_loss,
        "calibration_fit_performed": False,
        "ranking_at_k": ranking_metrics,
        "probability_distribution": {
            "minimum": float(test_probabilities.min()),
            "median": float(np.median(test_probabilities)),
            "mean": float(test_probabilities.mean()),
            "maximum": float(test_probabilities.max()),
            "samples_below_0_1_percent": int(((test_probabilities > 0) & (test_probabilities < 0.001)).sum()),
            "samples_at_least_90_percent": int((test_probabilities >= 0.9).sum()),
        },
    }

    if REPOSITORY_SCAN_PATH.exists():
        scanner = pd.read_csv(REPOSITORY_SCAN_PATH)
        missing_columns = [column for column in FEATURE_COLUMNS if column not in scanner]
        if missing_columns:
            raise ValueError(f"Saved repository scan is missing features: {missing_columns}")
        scanner_raw = scanner[FEATURE_COLUMNS].copy()
        scanner_imputed = scanner_raw.fillna(medians)
        scanner_scaled = pd.DataFrame(scaler.transform(scanner_imputed), columns=FEATURE_COLUMNS)
        if not np.isfinite(scanner_scaled.to_numpy(dtype=float)).all():
            raise ValueError("Saved repository scan produces non-finite standardized features.")
        scanner_scores = model.predict_proba(scanner_scaled)[:, list(model.classes_).index(1)]
        if not np.isfinite(scanner_scores).all() or ((scanner_scores < 0) | (scanner_scores > 1)).any():
            raise ValueError("Repository model scores must be finite probabilities in [0, 1].")
        scanner_decisions = model.decision_function(scanner_scaled)
        contribution_sums = (scanner_scaled.to_numpy() * model.coef_[0]).sum(axis=1) + model.intercept_[0]
        if not np.allclose(contribution_sums, scanner_decisions, atol=1e-10, rtol=1e-10):
            raise ValueError("Feature contributions do not reconstruct Logistic Regression decision scores.")
        scanner_contributions = _feature_contributions(
            scanner_raw,
            scanner_imputed,
            scanner_scaled,
            scanner["file"],
            scanner_scores,
            model,
            train_raw,
            medians,
        )
        scanner_contributions.to_csv(
            output_dir / "prediction_audit_top_file_contributions.csv",
            index=False,
        )
        scanner_stats = _feature_distribution(
            train_raw,
            scanner_raw,
            train_imputed,
            scanner_imputed,
            train_scaled,
            scanner_scaled,
        )
        scanner_stats.to_csv(output_dir / "prediction_audit_repository_feature_distribution.csv", index=False)
        scanner_rank = np.argsort(-scanner_scores, kind="stable")
        score_records = pd.DataFrame({
            "file": scanner["file"],
            "legacy_saved_score": scanner.get("risk_probability", pd.Series(np.nan, index=scanner.index)),
            "recomputed_logistic_regression_model_score": scanner_scores,
            "recomputed_threshold_label": np.where(scanner_scores > RISK_THRESHOLD, "HIGH", "LOW"),
        }).iloc[scanner_rank]
        score_records.to_csv(output_dir / "prediction_audit_repository_scores.csv", index=False)
        top_positions = scanner_rank[:TOP_FILES_FOR_CONTRIBUTIONS]
        high_score_summary = {
            "repository": json.loads(REPOSITORY_METADATA_PATH.read_text(encoding="utf-8")).get("repository")
            if REPOSITORY_METADATA_PATH.exists() else None,
            "captured_repository_feature_rows": int(len(scanner)),
            "feature_missing_cells": int(scanner_raw.isna().sum().sum()),
            "model_score_minimum": float(scanner_scores.min()),
            "model_score_median": float(np.median(scanner_scores)),
            "model_score_mean": float(scanner_scores.mean()),
            "model_score_maximum": float(scanner_scores.max()),
            "model_scores_at_least_90_percent": int((scanner_scores >= 0.9).sum()),
            "model_scores_at_least_50_percent": int((scanner_scores >= 0.5).sum()),
            "top_files": [
                {
                    "file": str(scanner["file"].iloc[position]),
                    "model_score": float(scanner_scores[position]),
                    "log_odds": float(model.decision_function(scanner_scaled.iloc[[position]])[0]),
                    "decision_reconstruction": float(
                        model.intercept_[0]
                        + (scanner_scaled.iloc[position].to_numpy() * model.coef_[0]).sum()
                    ),
                    "top_positive_contributions": scanner_contributions[
                        (scanner_contributions["rank"] == rank)
                    ].nlargest(5, "log_odds_contribution")[
                        ["feature", "raw_feature_value", "standardized_feature_value", "coefficient_per_standard_deviation", "log_odds_contribution"]
                    ].to_dict(orient="records"),
                    "top_negative_contributions": scanner_contributions[
                        (scanner_contributions["rank"] == rank)
                    ].nsmallest(3, "log_odds_contribution")[
                        ["feature", "raw_feature_value", "standardized_feature_value", "coefficient_per_standard_deviation", "log_odds_contribution"]
                    ].to_dict(orient="records"),
                }
                for rank, position in enumerate(top_positions, start=1)
            ],
        }
        out_of_range_summary = scanner_stats.set_index("feature")[
            "scanner_outside_training_range_count"
        ].astype(int).to_dict()
        scanner_source_model = (
            json.loads(REPOSITORY_METADATA_PATH.read_text(encoding="utf-8")).get("loaded_model")
            if REPOSITORY_METADATA_PATH.exists() else "unknown"
        )
    else:
        scanner_stats = pd.DataFrame()
        high_score_summary = {"available": False, "reason": f"{REPOSITORY_SCAN_PATH} does not exist."}
        out_of_range_summary = {}
        scanner_source_model = None

    evaluation_metrics = json.loads((RESULTS_DIR / "evaluation_metrics.json").read_text(encoding="utf-8"))
    saved_metrics = evaluation_metrics["LogisticRegression"]["combined"]
    comparison_keys = {
        "Accuracy": "accuracy",
        "Balanced_Accuracy": "balanced_accuracy",
        "Precision": "precision",
        "Recall": "recall",
        "F1_Score": "f1",
        "ROC_AUC": "roc_auc",
        "Average_Precision": "average_precision",
    }
    metric_deltas = {
        key: abs(model_metrics[report_key] - float(saved_metrics[key]))
        for key, report_key in comparison_keys.items()
    }
    report = {
        "model_file": str(MODEL_PATH),
        "model_classes": [int(value) for value in model.classes_],
        "positive_class": 1,
        "feature_columns": FEATURE_COLUMNS,
        "preprocessing": {
            "median_imputation": "training medians from data/processed/imputer_medians.json",
            "scaler": "data/processed/scaler.pkl",
            "training_transform_matches_saved_X_train": True,
            "test_transform_matches_saved_X_test": True,
            "api_preprocessing_contract": "raw ordered features -> training medians -> saved StandardScaler -> model",
            "double_scaling": False,
        },
        "model_configuration": {
            "class_weight": model.class_weight,
            "training_positive_fraction": float(pd.read_csv(PROCESSED_DIR / "y_train.csv").iloc[:, 0].mean()),
            "test_positive_fraction": prevalence,
        },
        "held_out_test_metrics": model_metrics,
        "saved_evaluation_metric_max_absolute_deltas": metric_deltas,
        "saved_evaluation_metrics_match": max(metric_deltas.values()) <= 1e-12,
        "calibration_interpretation": (
            "Uncalibrated model scores. Reliability, Brier score, log loss, and ECE are descriptive "
            "estimates on the existing held-out test set; no calibration model was fitted. The test "
            "set has few positives and must not be used both to fit calibration and claim independent performance."
        ),
        "scanner_diagnostics": {
            "source_artifact_model": scanner_source_model,
            "source_artifact_note": (
                "The saved Java Design Patterns feature snapshot predates the current Logistic Regression API "
                "deployment and its stored legacy scores were generated by the model named in its metadata. "
                "The audit recalculates Logistic Regression scores on captured features; this is not a new live scan."
            ),
            "feature_outside_training_raw_range_count": out_of_range_summary,
            "high_score_analysis": high_score_summary,
            "distribution_csv": "prediction_audit_repository_feature_distribution.csv",
            "top_contribution_csv": "prediction_audit_top_file_contributions.csv",
            "recomputed_score_csv": "prediction_audit_repository_scores.csv",
        },
        "calibration_bins_csv": "prediction_audit_calibration_bins.csv",
        "reliability_plot": "prediction_audit_reliability_diagram.png",
        "independent_external_repository_labels_available": False,
        "external_repository_ranking_metrics": None,
    }
    with open(output_dir / "prediction_audit.json", "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2, allow_nan=False)
    logger.info("Prediction audit saved under %s", output_dir)
    return report


if __name__ == "__main__":
    run_prediction_audit()
