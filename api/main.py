"""
FastAPI Backend API for SQAM Analytics Engine.
Provides real-time defect risk prediction and real repository scanning using:
- Real Java AST analysis (12 OO static metrics)
- Real Git history evolution mining (churn, revisions, developers)
- Authoritative 15-feature extraction schema matching training
"""

import os
import sys
import json
import shutil
import tempfile
import logging
from typing import Any, Dict, List, Optional
import git
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

# Ensure project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data.feature_extractor import (
    FEATURE_COLUMNS,
    STATIC_FEATURES,
    EVOLUTION_FEATURES,
    validate_feature_vector,
    extract_repository_features
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sqam_api")

app = FastAPI(
    title="SQAM Analytics Engine API",
    description="AI-Based Software Quality Prediction using Real Java Metrics and Git Evolution History"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ComponentMetrics(BaseModel):
    # 12 Java Static Metrics
    LOC: float
    WMC: float
    DIT: float
    NOC: float
    RFC: float
    LCOM5: float
    CBO: float
    NPA: float
    NPM: float
    NLE: float
    CBOI: float
    CD: float
    # 3 Git Evolution Metrics
    code_churn: float
    revision_count: float
    developer_count: float


class RepoUrl(BaseModel):
    url: str


def _load_model_and_scaler(model_name: str = "LogisticRegression_combined.pkl"):
    model_path = os.path.join(project_root, "src/models/saved", model_name)
    scaler_path = os.path.join(project_root, "data/processed", "scaler.pkl")
    medians_path = os.path.join(project_root, "data/processed", "imputer_medians.json")

    if not os.path.exists(model_path):
        raise HTTPException(
            status_code=500,
            detail=f"Model not found at {model_path}. Run training pipeline first."
        )
    if not os.path.exists(scaler_path):
        raise HTTPException(
            status_code=500,
            detail=f"Training scaler not found at {scaler_path}. Run preprocessing first."
        )
    if not os.path.exists(medians_path):
        raise HTTPException(
            status_code=500,
            detail=f"Training imputation medians not found at {medians_path}. Run preprocessing first."
        )

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    with open(medians_path, "r", encoding="utf-8") as medians_file:
        medians = json.load(medians_file)
    if getattr(scaler, "n_features_in_", None) != len(FEATURE_COLUMNS):
        raise HTTPException(status_code=500, detail="Saved scaler does not match the 15-feature model schema.")
    scaler_features = list(getattr(scaler, "feature_names_in_", []))
    if scaler_features and scaler_features != FEATURE_COLUMNS:
        raise HTTPException(status_code=500, detail="Saved scaler feature order differs from FEATURE_COLUMNS.")
    if list(medians) != FEATURE_COLUMNS or not np.isfinite(list(medians.values())).all():
        raise HTTPException(status_code=500, detail="Saved training medians do not match FEATURE_COLUMNS.")
    if list(getattr(model, "feature_names_in_", [])) != FEATURE_COLUMNS:
        raise HTTPException(status_code=500, detail="Saved model feature order differs from FEATURE_COLUMNS.")
    return model, scaler, medians


def _validate_model_input(X: pd.DataFrame, scaler: Any, medians: Dict[str, float]) -> pd.DataFrame:
    if list(X.columns) != FEATURE_COLUMNS:
        raise ValueError(f"Model input columns must match FEATURE_COLUMNS: {FEATURE_COLUMNS}")
    numeric = X.apply(pd.to_numeric, errors="raise")
    imputed = numeric.fillna(medians)
    if not np.isfinite(imputed.to_numpy(dtype=float)).all():
        raise ValueError("Model input contains infinite or non-finite feature values.")
    scaled = pd.DataFrame(scaler.transform(imputed), columns=FEATURE_COLUMNS, index=X.index)
    if not np.isfinite(scaled.to_numpy(dtype=float)).all():
        raise ValueError("Transformed model input contains infinite or non-finite feature values.")
    return scaled


def _rank_scan_results(results: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Rank by class-1 score, breaking exact ties by case-insensitive then exact file path."""
    valid_results = []
    failures = []
    for result in results:
        try:
            score = float(result["model_score"])
        except (KeyError, TypeError, ValueError):
            failures.append({
                "file": str(result.get("file", "")),
                "reason": "Model score was missing or not numeric.",
            })
            continue
        if not np.isfinite(score) or not 0.0 <= score <= 1.0:
            failures.append({
                "file": str(result.get("file", "")),
                "reason": "Model score was not finite or outside the class-score range [0, 1].",
            })
            continue
        valid_results.append({**result, "model_score": score, "risk_probability": score})

    valid_results.sort(key=lambda result: (
        -result["model_score"],
        str(result.get("file", "")).casefold(),
        str(result.get("file", "")),
    ))

    total = len(valid_results)
    tied_groups = []
    index = 0
    while index < total:
        end = index + 1
        while end < total and valid_results[end]["model_score"] == valid_results[index]["model_score"]:
            end += 1
        tied_groups.append((index, end))
        index = end

    for start, end in tied_groups:
        middle_rank_position = (start + end - 1) / 2
        relative_position = middle_rank_position / max(total - 1, 1)
        if start == 0:
            priority = "Highest priority"
        elif relative_position <= 0.25:
            priority = "High relative priority"
        elif relative_position <= 0.75:
            priority = "Medium relative priority"
        else:
            priority = "Lower relative priority"

        for result_index in range(start, end):
            valid_results[result_index]["rank"] = result_index + 1
            valid_results[result_index]["priority"] = priority
            valid_results[result_index]["score_tie_count"] = end - start

    return valid_results, failures


@app.get("/")
def read_root():
    return {
        "message": "Welcome to SQAM Analytics Engine API",
        "supported_features": FEATURE_COLUMNS,
        "feature_count": len(FEATURE_COLUMNS),
        "status": "online"
    }


@app.get("/evaluation")
def get_evaluation_metrics():
    metrics_path = os.path.join(project_root, "data/results", "evaluation_metrics.json")
    if not os.path.exists(metrics_path):
        raise HTTPException(status_code=404, detail="Evaluation metrics not found. Run evaluation first.")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
    return metrics


@app.get("/prediction-audit")
def get_prediction_audit():
    audit_path = os.path.join(project_root, "data/results", "prediction_audit.json")
    distribution_path = os.path.join(
        project_root,
        "data/results",
        "prediction_audit_repository_feature_distribution.csv",
    )
    calibration_path = os.path.join(
        project_root,
        "data/results",
        "prediction_audit_calibration_bins.csv",
    )
    if not all(os.path.exists(path) for path in (audit_path, distribution_path, calibration_path)):
        raise HTTPException(
            status_code=404,
            detail="Prediction audit artifacts are not available. Run the existing prediction audit first.",
        )

    with open(audit_path, "r", encoding="utf-8") as audit_file:
        audit = json.load(audit_file)

    scanner_diagnostics = audit.get("scanner_diagnostics", {})
    high_score_analysis = scanner_diagnostics.get("high_score_analysis", {})
    return {
        "model_file": audit.get("model_file"),
        "feature_columns": audit.get("feature_columns"),
        "preprocessing": audit.get("preprocessing"),
        "model_configuration": audit.get("model_configuration"),
        "held_out_test_metrics": audit.get("held_out_test_metrics"),
        "saved_evaluation_metrics_match": audit.get("saved_evaluation_metrics_match"),
        "calibration_interpretation": audit.get("calibration_interpretation"),
        "independent_external_repository_labels_available": audit.get(
            "independent_external_repository_labels_available"
        ),
        "scanner_diagnostics": {
            "source_artifact_model": scanner_diagnostics.get("source_artifact_model"),
            "source_artifact_note": scanner_diagnostics.get("source_artifact_note"),
            "feature_outside_training_raw_range_count": scanner_diagnostics.get(
                "feature_outside_training_raw_range_count"
            ),
            "high_score_analysis": {
                key: high_score_analysis.get(key)
                for key in (
                    "repository",
                    "captured_repository_feature_rows",
                    "feature_missing_cells",
                    "model_score_median",
                    "model_score_mean",
                    "model_score_maximum",
                    "model_scores_at_least_90_percent",
                )
            },
        },
        "scanner_feature_distribution": pd.read_csv(distribution_path).to_dict(orient="records"),
        "calibration_bins": pd.read_csv(calibration_path).to_dict(orient="records"),
    }


@app.get("/feature-importance")
def get_feature_importance():
    importance_path = os.path.join(
        project_root,
        "data/results",
        "logistic_regression_combined_feature_coefficients.csv",
    )
    if not os.path.exists(importance_path):
        raise HTTPException(status_code=404, detail="Feature importance not found. Run explainability first.")
    df = pd.read_csv(importance_path)
    return df.to_dict(orient="records")


@app.post("/predict")
def predict_defect_risk(metrics: ComponentMetrics):
    """
    Scales the raw 15-feature vector using the saved training scaler before prediction.
    """
    model, scaler, medians = _load_model_and_scaler()

    try:
        input_data = metrics.model_dump() if hasattr(metrics, "model_dump") else metrics.dict()
        input_df = validate_feature_vector(input_data)
        model_input = _validate_model_input(input_df, scaler, medians)
        pred = int(model.predict(model_input)[0])
        positive_class_index = list(model.classes_).index(1)
        prob = float(model.predict_proba(model_input)[0][positive_class_index])

        return {
            "prediction": pred,
            "probability": prob,
            "model_score": prob,
            "risk_level": "HIGH" if pred == 1 else "LOW",
            "probability_interpretation": "uncalibrated_model_estimate",
            "features_used": FEATURE_COLUMNS
        }
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scan-repo")
def scan_repository(
    repo: RepoUrl,
    limit: int = Query(
        default=50,
        ge=0,
        le=10000,
        description="Maximum ranked results to return. Use 0 to return all successfully scored files.",
    ),
):
    """
    Clones a Git repository, performs real Java static AST analysis,
    mines real Git evolution metrics, and predicts defect risk.
    Does NOT use mock or hardcoded values.
    """
    url = repo.url.strip()
    is_valid_url = url.startswith(("http://", "https://", "git://", "file://")) or os.path.isdir(url)
    if not is_valid_url:
        raise HTTPException(
            status_code=400,
            detail="Invalid repository URL or path. Must start with http://, https://, or be a valid repository."
        )

    model, scaler, medians = _load_model_and_scaler()
    temp_dir = tempfile.mkdtemp(prefix="sqam_scan_")
    logger.info(f"Initiating repository scan for: {url} in temporary workspace: {temp_dir}")

    try:
        # 1. Clone repository
        try:
            logger.info(f"Cloning {url}...")
            cloned_repo = git.Repo.clone_from(url, temp_dir)
            repository_commit = cloned_repo.head.commit.hexsha if cloned_repo.head.is_valid() else None
        except Exception as e:
            logger.error(f"Failed to clone repository {url}: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to clone repository: {str(e)}")

        # 2. Extract real features (12 static AST metrics + 3 real Git metrics)
        logger.info(f"Extracting static AST metrics and mining Git evolution history...")
        repo_features_df = extract_repository_features(temp_dir)

        total_files = len(repo_features_df)
        logger.info(f"Repository feature extraction complete. Total Java files analyzed: {total_files}")

        if total_files == 0:
            return {
                "message": "No Java source files were found in the specified repository.",
                "repository": url,
                "repository_commit": repository_commit,
                "java_files_discovered": repo_features_df.attrs.get("java_files_discovered", 0),
                "total_java_files_analyzed": 0,
                "files_analyzed": 0,
                "files_scored": 0,
                "files_returned": 0,
                "result_limit": limit or None,
                "prediction_failures": [],
                "classes_discovered": repo_features_df.attrs.get("classes_discovered", 0),
                "classes_scored": 0,
                "context_parse_failures": repo_features_df.attrs.get("context_parse_failures", []),
                "analysis_failures": repo_features_df.attrs.get("analysis_failures", []),
                "unresolved_project_references": repo_features_df.attrs.get("unresolved_project_references", 0),
                "unidentified_class_files": repo_features_df.attrs.get("unidentified_class_files", []),
                "files": []
            }

        # 3. Apply the same training scaler used before model fitting.
        X_repo = _validate_model_input(repo_features_df[FEATURE_COLUMNS].copy(), scaler, medians)

        # 4. Use the defective class probability.
        positive_class_index = list(model.classes_).index(1)
        probabilities = model.predict_proba(X_repo)[:, positive_class_index]
        predictions = model.predict(X_repo)
        if probabilities.shape[0] != total_files or len(predictions) != total_files:
            raise ValueError("Model prediction output does not match the extracted Java file count.")
        unidentified_class_files = repo_features_df.attrs.get("unidentified_class_files", [])
        classes_discovered = repo_features_df.attrs.get("classes_discovered", total_files)
        classes_scored = repo_features_df.attrs.get("classes_scored", total_files)

        # 5. Build results (with backward compatibility for frontend)
        results = []
        prediction_failures = []
        for i, row in repo_features_df.iterrows():
            try:
                prob = float(probabilities[i])
                prediction = int(predictions[i])
                if not np.isfinite(prob) or not 0.0 <= prob <= 1.0:
                    raise ValueError("Class-1 score was not finite or outside [0, 1].")
                if prediction not in (0, 1) or float(predictions[i]) != prediction:
                    raise ValueError("Predicted class was not a valid binary class label.")
            except (TypeError, ValueError, OverflowError) as error:
                prediction_failures.append({
                    "file": str(row["file"]),
                    "reason": str(error),
                })
                continue
            pred_level = "HIGH" if prediction == 1 else "LOW"

            results.append({
                "file": row["file"],
                "class_name": row["class_name"],
                "class_identity": row["class_identity"],
                # Backward-compatible fields expected by existing frontend UI
                "loc": int(row["LOC"]),
                "churn": int(row["code_churn"]),
                "revisions": int(row["revision_count"]),
                "risk_probability": prob,
                "model_score": prob,
                "risk_level": pred_level,
                # Full 15 extracted metrics for transparency and debugging
                "metrics": {
                    col: float(row[col]) for col in FEATURE_COLUMNS
                }
            })

        ranked_results, invalid_score_failures = _rank_scan_results(results)
        prediction_failures.extend(invalid_score_failures)
        top_results = ranked_results[:limit] if limit else ranked_results

        logger.info(
            "Scan complete. Scored %s Java files and returning %s ranked results (limit=%s).",
            len(ranked_results),
            len(top_results),
            limit or "all",
        )
        return {
            "repository": url,
            "repository_commit": repository_commit,
            "probability_interpretation": "uncalibrated_model_estimate",
            "score_notice": (
                "Scores are model estimates for prioritizing manual review; they do not confirm defects "
                "and have not been calibrated for this repository."
            ),
            "java_files_discovered": repo_features_df.attrs.get("java_files_discovered", total_files),
            "total_java_files_analyzed": total_files,
            "files_analyzed": total_files,
            "classes_discovered": repo_features_df.attrs.get("classes_discovered", total_files),
            "files_scored": len(ranked_results),
            "files_returned": len(top_results),
            "result_limit": limit or None,
            "prediction_failures": prediction_failures,
            "ranking_tie_breaker": (
                "Equal class-1 scores are ordered by file path case-insensitively, then exact path; "
                "tied files share the same relative-priority label."
            ),
            "priority_rule": (
                "Rank 1 is Highest priority; remaining score-tie groups are assigned relative tiers by "
                "their midpoint percentile of the complete ranked list (top quartile High, middle half "
                "Medium, final quartile Lower). These are relative ordering labels, not absolute defect-risk classes."
            ),
            "classes_scored": classes_scored,
            "unidentified_class_file_count": len(unidentified_class_files),
            "unidentified_class_files": unidentified_class_files,
            "class_declarations_not_individually_scored": max(0, classes_discovered - classes_scored),
            "non_primary_classes_not_scored": max(0, classes_discovered - classes_scored - len(unidentified_class_files)),
            "non_primary_class_reason": "The scanner predicts one primary top-level class per Java file; additional and nested declarations are not individually scored.",
            "context_parse_failures": repo_features_df.attrs.get("context_parse_failures", []),
            "analysis_failures": repo_features_df.attrs.get("analysis_failures", []),
            "unresolved_project_references": repo_features_df.attrs.get("unresolved_project_references", 0),
            "files": top_results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error scanning repository: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up cloned repository
        shutil.rmtree(temp_dir, ignore_errors=True)
