import os
import joblib
import pandas as pd
import numpy as np
import shap
from typing import Dict, Any, List, Optional
from api.feature_processor import FeatureProcessor, ALL_FEATURES, STATIC_FEATURES

FEATURE_METRIC_LABELS = {
    "WMC": "Weighted Methods per Class (Complexity)",
    "DIT": "Depth of Inheritance Tree",
    "NOC": "Number of Children (Subclasses)",
    "CBO": "Coupling Between Object Classes",
    "RFC": "Response For a Class",
    "LCOM5": "Lack of Cohesion of Methods (LCOM5)",
    "NPA": "Number of Public Attributes",
    "NPM": "Number of Public Methods",
    "NLE": "Nesting Level Else-If (Max Nesting)",
    "CBOI": "Inverse Coupling (Afferent Coupling)",
    "CD": "Comment Density",
    "LOC": "Lines of Code",
    "code_churn": "Historical Code Churn",
    "revision_count": "Commit Revision Count",
    "developer_count": "Distinct Developer Count"
}

class ExplainabilityService:
    """
    Computes SHAP explanations and generates actionable natural-language insights
    for defect-risk predictions.
    """

    def __init__(self, models_dir: str = "src/models/saved", results_dir: str = "data/results"):
        self.models_dir = models_dir
        self.results_dir = results_dir
        self.feature_processor = FeatureProcessor()
        self.explainers: Dict[str, Any] = {}
        self._init_explainers()

    def _init_explainers(self):
        """
        Initializes background dataset and SHAP explainers for instant file-level explanations.
        """
        try:
            # Load background training samples for SHAP
            train_path = "data/processed/X_train.csv"
            if os.path.exists(train_path):
                X_train = pd.read_csv(train_path)
                bg_sample = X_train.sample(n=min(50, len(X_train)), random_state=42)
            else:
                bg_sample = pd.DataFrame(np.zeros((10, len(ALL_FEATURES))), columns=ALL_FEATURES)

            # 1. LinearExplainer for Logistic Regression Combined
            lr_path = os.path.join(self.models_dir, "LogisticRegression_combined.pkl")
            if os.path.exists(lr_path):
                lr_model = joblib.load(lr_path)
                self.explainers["LogisticRegression_combined"] = shap.LinearExplainer(
                    lr_model, bg_sample
                )

            # 2. TreeExplainer for Random Forest Combined
            rf_path = os.path.join(self.models_dir, "RandomForest_combined.pkl")
            if os.path.exists(rf_path):
                rf_model = joblib.load(rf_path)
                self.explainers["RandomForest_combined"] = shap.TreeExplainer(rf_model)

        except Exception as e:
            print(f"Warning: Could not initialize SHAP explainers: {e}")

    def explain_file_prediction(
        self,
        file_metrics: Dict[str, Any],
        model_name: str = "LogisticRegression_combined"
    ) -> Dict[str, Any]:
        """
        Calculates SHAP contributions for a single file.
        """
        # Prepare single row DataFrame
        df_raw = self.feature_processor.prepare_dataframe([file_metrics])
        
        # Scaling
        is_static = "static" in model_name
        if is_static:
            df_scaled = self.feature_processor.transform_static(df_raw)
            features = STATIC_FEATURES
        else:
            df_scaled = self.feature_processor.transform_combined(df_raw)
            features = ALL_FEATURES

        feature_contributions = []
        base_value = 0.5

        # Attempt SHAP explainer
        explainer = self.explainers.get(model_name)
        if explainer is not None and not is_static:
            try:
                shap_res = explainer.shap_values(df_scaled)
                # Handle binary classification shapes
                if isinstance(shap_res, list) and len(shap_res) > 1:
                    shap_vals = shap_res[1][0]
                elif isinstance(shap_res, np.ndarray) and len(shap_res.shape) == 3:
                    shap_vals = shap_res[0, :, 1]
                else:
                    shap_vals = np.array(shap_res).flatten()

                if hasattr(explainer, 'expected_value'):
                    exp_val = explainer.expected_value
                    base_value = float(exp_val[1] if isinstance(exp_val, (list, np.ndarray)) else exp_val)

                for feat, s_val in zip(features, shap_vals):
                    val = float(file_metrics.get(feat, 0.0))
                    s_float = float(s_val)
                    feature_contributions.append({
                        "feature": feat,
                        "label": FEATURE_METRIC_LABELS.get(feat, feat),
                        "raw_value": val,
                        "shap_value": round(s_float, 4),
                        "impact": "Increases Risk" if s_float > 0 else "Decreases Risk",
                        "absolute_impact": abs(round(s_float, 4))
                    })
            except Exception as e:
                feature_contributions = self._compute_linear_weights(df_scaled, features, file_metrics)
        else:
            # Fallback to model weights or feature deviation
            feature_contributions = self._compute_linear_weights(df_scaled, features, file_metrics)

        # Sort contributions by absolute impact descending
        feature_contributions.sort(key=lambda x: x["absolute_impact"], reverse=True)

        # Generate natural language narrative
        narrative = self._generate_diagnostic_narrative(file_metrics, feature_contributions)

        return {
            "file_name": file_metrics.get("file_name", "Unknown"),
            "file_path": file_metrics.get("file_path", ""),
            "base_value": round(base_value, 4),
            "feature_contributions": feature_contributions,
            "top_drivers": feature_contributions[:5],
            "narrative_explanation": narrative
        }

    def _compute_linear_weights(
        self,
        df_scaled: pd.DataFrame,
        features: List[str],
        file_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Calculates contributions using Logistic Regression coefficients as a deterministic fallback.
        """
        contributions = []
        lr_path = os.path.join(self.models_dir, "LogisticRegression_combined.pkl")
        coefs = None
        if os.path.exists(lr_path):
            try:
                lr = joblib.load(lr_path)
                coefs = dict(zip(ALL_FEATURES, lr.coef_[0]))
            except Exception:
                pass

        for feat in features:
            scaled_val = float(df_scaled[feat].iloc[0])
            raw_val = float(file_metrics.get(feat, 0.0))
            weight = coefs.get(feat, 0.5) if coefs else 0.5
            impact_val = scaled_val * weight

            contributions.append({
                "feature": feat,
                "label": FEATURE_METRIC_LABELS.get(feat, feat),
                "raw_value": raw_val,
                "shap_value": round(impact_val, 4),
                "impact": "Increases Risk" if impact_val > 0 else "Decreases Risk",
                "absolute_impact": abs(round(impact_val, 4))
            })

        return contributions

    def _generate_diagnostic_narrative(
        self,
        metrics: Dict[str, Any],
        contributions: List[Dict[str, Any]]
    ) -> str:
        """
        Produces human-readable diagnostic analysis tailored to software engineering practices.
        """
        positives = [c for c in contributions if c["shap_value"] > 0]
        negatives = [c for c in contributions if c["shap_value"] < 0]

        churn = metrics.get("code_churn", 0)
        revisions = metrics.get("revision_count", 0)
        devs = metrics.get("developer_count", 0)
        wmc = metrics.get("WMC", 0)
        cbo = metrics.get("CBO", 0)
        loc = metrics.get("LOC", 0)

        insights = []
        if churn > 500 or revisions > 20:
            insights.append(
                f"Historical volatility is pronounced ({churn} total churn lines across {revisions} commits by {devs} developers), "
                "which empirical studies show correlates strongly with latent defects."
            )
        if wmc > 25:
            insights.append(
                f"High cyclomatic complexity (WMC of {wmc:.0f}) indicates intricate branching logic that increases testing difficulty."
            )
        if cbo > 15:
            insights.append(
                f"Class coupling (CBO: {cbo:.0f}) exceeds recommended thresholds, making this component fragile to upstream API changes."
            )
        if loc > 500:
            insights.append(
                f"The class spans {loc:.0f} lines of code, suggesting potential 'God Class' tendencies."
            )

        if not insights:
            insights.append(
                "Metric signatures are well-balanced with modest complexity, low coupling, and stable revision history."
            )

        top_drivers_str = ", ".join([f"{c['label']} (+{c['shap_value']:.2f})" for c in positives[:3]])
        if top_drivers_str:
            conclusion = f"Primary risk amplifiers: {top_drivers_str}."
        else:
            conclusion = "No significant risk-elevating factors detected."

        return " ".join(insights) + " " + conclusion

    def get_global_feature_importance(self) -> List[Dict[str, Any]]:
        """
        Returns precomputed global feature importance from training results.
        """
        csv_path = os.path.join(self.results_dir, "feature_importance.csv")
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                records = []
                for _, row in df.iterrows():
                    feat = row["Feature"]
                    records.append({
                        "feature": feat,
                        "label": FEATURE_METRIC_LABELS.get(feat, feat),
                        "importance": round(float(row["Importance"]), 4),
                        "category": "Git Evolution" if feat in ["code_churn", "revision_count", "developer_count"] else "Static OO Metric"
                    })
                return records
            except Exception:
                pass

        # Fallback to model coefficients if CSV missing
        return []

