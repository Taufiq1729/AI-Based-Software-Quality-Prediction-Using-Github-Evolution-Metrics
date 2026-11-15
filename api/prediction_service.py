import os
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from api.feature_processor import FeatureProcessor, STATIC_FEATURES, ALL_FEATURES

SUPPORTED_MODELS = {
    "LogisticRegression_combined": {
        "file": "LogisticRegression_combined.pkl",
        "type": "combined",
        "name": "Logistic Regression (Combined)",
        "description": "Primary model utilizing 12 Static OO Metrics + 3 Git Evolution Metrics"
    },
    "LogisticRegression_static": {
        "file": "LogisticRegression_static.pkl",
        "type": "static",
        "name": "Logistic Regression (Static Only)",
        "description": "Baseline model utilizing 12 Static OO Metrics only"
    },
    "RandomForest_combined": {
        "file": "RandomForest_combined.pkl",
        "type": "combined",
        "name": "Random Forest (Combined)",
        "description": "Ensemble tree classifier with 15 static and evolution features"
    },
    "RandomForest_static": {
        "file": "RandomForest_static.pkl",
        "type": "static",
        "name": "Random Forest (Static Only)",
        "description": "Ensemble tree classifier with 12 static features only"
    },
    "DecisionTree_combined": {
        "file": "DecisionTree_combined.pkl",
        "type": "combined",
        "name": "Decision Tree (Combined)",
        "description": "Single decision tree with 15 static and evolution features"
    },
    "DecisionTree_static": {
        "file": "DecisionTree_static.pkl",
        "type": "static",
        "name": "Decision Tree (Static Only)",
        "description": "Single decision tree with 12 static features only"
    }
}

class PredictionService:
    """
    Manages loading and running inference across all 6 Machine Learning configurations.
    """

    def __init__(self, models_dir: str = "src/models/saved"):
        self.models_dir = models_dir
        self.feature_processor = FeatureProcessor()
        self.loaded_models: Dict[str, Any] = {}
        self._load_all_models()

    def _load_all_models(self):
        for key, info in SUPPORTED_MODELS.items():
            model_path = os.path.join(self.models_dir, info["file"])
            if os.path.exists(model_path):
                try:
                    self.loaded_models[key] = joblib.load(model_path)
                except Exception as e:
                    print(f"Warning: Could not load model {key}: {e}")
            else:
                print(f"Warning: Model file {model_path} does not exist.")

    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Returns list of configured model configurations.
        """
        available = []
        for key, info in SUPPORTED_MODELS.items():
            is_loaded = key in self.loaded_models
            available.append({
                "id": key,
                "name": info["name"],
                "type": info["type"],
                "description": info["description"],
                "is_primary": (key == "LogisticRegression_combined"),
                "is_loaded": is_loaded
            })
        return available

    def predict_repository_files(
        self,
        file_records: List[Dict[str, Any]],
        model_name: str = "LogisticRegression_combined",
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Runs defect-risk prediction on all file records in the repository.
        """
        if not file_records:
            return {
                "files": [],
                "summary": {
                    "total_analyzed": 0,
                    "high_risk_count": 0,
                    "low_risk_count": 0,
                    "average_risk_score": 0.0,
                    "model_used": model_name,
                    "threshold_applied": threshold
                },
                "risk_distribution": {"buckets": [], "top_risk_files": []}
            }

        # Validate requested model
        if model_name not in SUPPORTED_MODELS:
            model_name = "LogisticRegression_combined"

        model = self.loaded_models.get(model_name)
        if model is None:
            raise RuntimeError(
                f"Model '{model_name}' is not loaded. Ensure model files exist in '{self.models_dir}'."
            )

        model_type = SUPPORTED_MODELS[model_name]["type"]
        df_raw = self.feature_processor.prepare_dataframe(file_records)

        # Scale according to model input requirements
        if model_type == "static":
            df_scaled = self.feature_processor.transform_static(df_raw)
            features_used = STATIC_FEATURES
        else:
            df_scaled = self.feature_processor.transform_combined(df_raw)
            features_used = ALL_FEATURES

        # Inference
        try:
            probabilities = model.predict_proba(df_scaled)[:, 1]
        except AttributeError:
            probabilities = model.predict(df_scaled)

        # Build individual file predictions
        results = []
        high_risk_count = 0
        low_risk_count = 0
        risk_scores = []

        for idx, rec in enumerate(file_records):
            score = float(probabilities[idx])
            risk_scores.append(score)
            is_high_risk = score > threshold
            if is_high_risk:
                high_risk_count += 1
            else:
                low_risk_count += 1

            # Determine key contributing metric factors for this file
            contributing = []
            if rec.get("code_churn", 0) > 300:
                contributing.append(f"High historical code churn ({int(rec['code_churn'])} lines modified)")
            if rec.get("revision_count", 0) > 15:
                contributing.append(f"Frequent historical modifications ({int(rec['revision_count'])} revisions)")
            if rec.get("WMC", 0) > 20:
                contributing.append(f"Elevated cyclomatic complexity (WMC: {rec['WMC']:.0f})")
            if rec.get("CBO", 0) > 15:
                contributing.append(f"Extensive coupling with other classes (CBO: {rec['CBO']:.0f})")
            if rec.get("LOC", 0) > 400:
                contributing.append(f"Substantial class size (LOC: {rec['LOC']:.0f})")
            if rec.get("developer_count", 0) > 5:
                contributing.append(f"Diffused code ownership ({int(rec['developer_count'])} distinct developers)")
            if rec.get("CD", 0) < 0.05 and rec.get("LOC", 0) > 100:
                contributing.append("Sparse documentation relative to code size")

            if not contributing:
                contributing = ["Stable architectural metrics within nominal thresholds"]

            file_result = {
                "file_path": rec["file_path"],
                "file_name": rec["file_name"],
                "class_name": rec.get("class_name", ""),
                # Metrics
                "LOC": rec["LOC"],
                "WMC": rec["WMC"],
                "DIT": rec["DIT"],
                "NOC": rec["NOC"],
                "CBO": rec["CBO"],
                "RFC": rec["RFC"],
                "LCOM5": rec["LCOM5"],
                "NPA": rec["NPA"],
                "NPM": rec["NPM"],
                "NLE": rec["NLE"],
                "CBOI": rec["CBOI"],
                "CD": rec["CD"],
                "code_churn": rec["code_churn"],
                "revision_count": rec["revision_count"],
                "developer_count": rec["developer_count"],
                # Prediction details
                "risk_score": round(score, 4),
                "risk_level": "HIGH" if is_high_risk else "LOW",
                "model_used": SUPPORTED_MODELS[model_name]["name"],
                "model_id": model_name,
                "contributing_factors": contributing[:4],
                "explanation_summary": (
                    f"Class '{rec.get('class_name', rec['file_name'])}' has a defect-risk score of {score:.1%}. "
                    + ("Key concerns: " + "; ".join(contributing[:2]) + "." if is_high_risk else "Metrics indicate low structural risk.")
                )
            }
            results.append(file_result)

        # Sort files by risk score descending
        results.sort(key=lambda x: x["risk_score"], reverse=True)

        avg_score = round(float(np.mean(risk_scores)), 4) if risk_scores else 0.0

        # Score distribution histogram buckets: [0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0]
        bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.01]
        bin_labels = ["0.0 - 0.2 (Very Low)", "0.2 - 0.4 (Low)", "0.4 - 0.6 (Moderate)", "0.6 - 0.8 (High)", "0.8 - 1.0 (Critical)"]
        counts, _ = np.histogram(risk_scores, bins=bins)
        distribution_buckets = [
            {"range": label, "count": int(count), "percentage": round(int(count) / len(risk_scores) * 100, 1)}
            for label, count in zip(bin_labels, counts)
        ]

        summary = {
            "total_analyzed": len(results),
            "high_risk_count": high_risk_count,
            "low_risk_count": low_risk_count,
            "high_risk_percentage": round(high_risk_count / len(results) * 100, 1) if results else 0,
            "low_risk_percentage": round(low_risk_count / len(results) * 100, 1) if results else 0,
            "average_risk_score": avg_score,
            "model_used": SUPPORTED_MODELS[model_name]["name"],
            "model_id": model_name,
            "threshold_applied": threshold,
            "disclaimer": (
                "The defect-risk score is a relative ranking indicator derived from structural complexity "
                "and Git evolution patterns. It highlights components that warrant deeper peer review, "
                "not confirmed defects or calibrated probabilities."
            )
        }

        top_risk_files = [
            {
                "file_name": f["file_name"],
                "file_path": f["file_path"],
                "risk_score": f["risk_score"],
                "risk_level": f["risk_level"],
                "loc": f["LOC"],
                "churn": f["code_churn"]
            }
            for f in results[:10]
        ]

        return {
            "files": results,
            "summary": summary,
            "distribution": {
                "buckets": distribution_buckets,
                "top_risk_files": top_risk_files
            }
        }

