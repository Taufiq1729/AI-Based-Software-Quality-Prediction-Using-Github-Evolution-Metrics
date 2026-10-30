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
from typing import Dict, Any, List, Optional
import git
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
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


def _load_model_and_scaler(model_name: str = "RandomForest_combined.pkl"):
    model_path = os.path.join(project_root, "src/models/saved", model_name)
    scaler_path = os.path.join(project_root, "data/processed", "scaler.pkl")
    imputer_path = os.path.join(project_root, "data/processed", "imputer_medians.json")

    if not os.path.exists(model_path):
        raise HTTPException(
            status_code=500,
            detail=f"Model not found at {model_path}. Run training pipeline first."
        )
    if not os.path.exists(scaler_path):
        raise HTTPException(
            status_code=500,
            detail=f"Scaler not found at {scaler_path}. Run preprocessing first."
        )

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    medians = {}
    if os.path.exists(imputer_path):
        with open(imputer_path, "r") as f:
            medians = json.load(f)

    return model, scaler, medians


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


@app.get("/feature-importance")
def get_feature_importance():
    importance_path = os.path.join(project_root, "data/results", "feature_importance.csv")
    if not os.path.exists(importance_path):
        raise HTTPException(status_code=404, detail="Feature importance not found. Run explainability first.")
    df = pd.read_csv(importance_path)
    return df.to_dict(orient="records")


@app.post("/predict")
def predict_defect_risk(metrics: ComponentMetrics):
    """
    Predicts defect probability and risk level from the 15 input metrics.
    Validates feature order and schema to match model training exactly.
    """
    model, scaler, medians = _load_model_and_scaler()

    try:
        # Validate feature vector ordering and types
        input_data = metrics.model_dump() if hasattr(metrics, "model_dump") else metrics.dict()
        input_df = validate_feature_vector(input_data)

        # Impute if needed using training medians
        if medians:
            input_df = input_df.fillna(medians)

        # Scale using pre-fitted training scaler
        scaled_array = scaler.transform(input_df)
        scaled_df = pd.DataFrame(scaled_array, columns=FEATURE_COLUMNS)

        # Predict
        prob = float(model.predict_proba(scaled_df)[0][1])
        pred = int(prob > 0.5)

        return {
            "prediction": pred,
            "probability": prob,
            "risk_level": "HIGH" if pred == 1 else "LOW",
            "features_used": FEATURE_COLUMNS
        }
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scan-repo")
def scan_repository(repo: RepoUrl):
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
                "files_scored": 0,
                "classes_discovered": repo_features_df.attrs.get("classes_discovered", 0),
                "classes_scored": 0,
                "context_parse_failures": repo_features_df.attrs.get("context_parse_failures", []),
                "analysis_failures": repo_features_df.attrs.get("analysis_failures", []),
                "unresolved_project_references": repo_features_df.attrs.get("unresolved_project_references", 0),
                "unidentified_class_files": repo_features_df.attrs.get("unidentified_class_files", []),
                "files": []
            }

        # 3. Prepare feature vector for prediction strictly in FEATURE_COLUMNS order
        X_repo = repo_features_df[FEATURE_COLUMNS].copy()
        if medians:
            X_repo = X_repo.fillna(medians)

        # Scale using saved scaler (preserves feature names to avoid sklearn warnings)
        X_scaled_array = scaler.transform(X_repo)
        X_scaled_df = pd.DataFrame(X_scaled_array, columns=FEATURE_COLUMNS)

        # 4. Run model inference
        probabilities = model.predict_proba(X_scaled_df)[:, 1]
        unidentified_class_files = repo_features_df.attrs.get("unidentified_class_files", [])
        classes_discovered = repo_features_df.attrs.get("classes_discovered", total_files)
        classes_scored = repo_features_df.attrs.get("classes_scored", total_files)

        # 5. Build results (with backward compatibility for frontend)
        results = []
        for i, row in repo_features_df.iterrows():
            prob = float(probabilities[i])
            pred_level = "HIGH" if prob > 0.5 else "LOW"

            results.append({
                "file": row["file"],
                "class_name": row["class_name"],
                "class_identity": row["class_identity"],
                # Backward-compatible fields expected by existing frontend UI
                "loc": int(row["LOC"]),
                "churn": int(row["code_churn"]),
                "revisions": int(row["revision_count"]),
                "risk_probability": prob,
                "risk_level": pred_level,
                # Full 15 extracted metrics for transparency and debugging
                "metrics": {
                    col: float(row[col]) for col in FEATURE_COLUMNS
                }
            })

        # Sort files by highest defect probability
        results.sort(key=lambda x: x["risk_probability"], reverse=True)
        top_results = results[:50] # Return top 50 highest risk files

        logger.info(f"Scan complete. Returning top {len(top_results)} defect-prone files.")
        return {
            "repository": url,
            "repository_commit": repository_commit,
            "java_files_discovered": repo_features_df.attrs.get("java_files_discovered", total_files),
            "total_java_files_analyzed": total_files,
            "classes_discovered": repo_features_df.attrs.get("classes_discovered", total_files),
            "files_scored": repo_features_df.attrs.get("files_scored", len(repo_features_df)),
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
