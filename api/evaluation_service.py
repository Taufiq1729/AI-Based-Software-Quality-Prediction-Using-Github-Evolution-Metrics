import os
import json
from typing import Dict, Any, List, Optional

# Official Research Benchmark results cited from the paper (Section 6)
RESEARCH_BENCHMARK_RESULTS = {
    "LogisticRegression": {
        "model_name": "Logistic Regression",
        "static": {
            "Average_Precision": 0.0203,
            "ROC_AUC": 0.6892,
            "Precision": 0.0185,
            "Recall": 0.4500,
            "F1_Score": 0.0355,
            "Accuracy": 0.7410
        },
        "combined": {
            "Average_Precision": 0.0276,
            "ROC_AUC": 0.7890,
            "Precision": 0.0244,
            "Recall": 0.5600,
            "F1_Score": 0.0468,
            "Accuracy": 0.7784
        },
        "improvement_ap_pct": 36.0,
        "improvement_auc_delta": 0.0998
    },
    "DecisionTree": {
        "model_name": "Decision Tree",
        "static": {
            "Average_Precision": 0.0097,
            "ROC_AUC": 0.5980,
            "Precision": 0.0110,
            "Recall": 0.3200,
            "F1_Score": 0.0212,
            "Accuracy": 0.8120
        },
        "combined": {
            "Average_Precision": 0.0114,
            "ROC_AUC": 0.6450,
            "Precision": 0.0135,
            "Recall": 0.3800,
            "F1_Score": 0.0260,
            "Accuracy": 0.8240
        },
        "improvement_ap_pct": 17.5,
        "improvement_auc_delta": 0.0470
    },
    "RandomForest": {
        "model_name": "Random Forest",
        "static": {
            "Average_Precision": 0.0104,
            "ROC_AUC": 0.6810,
            "Precision": 0.0125,
            "Recall": 0.3500,
            "F1_Score": 0.0241,
            "Accuracy": 0.8850
        },
        "combined": {
            "Average_Precision": 0.0160,
            "ROC_AUC": 0.7320,
            "Precision": 0.0180,
            "Recall": 0.4400,
            "F1_Score": 0.0345,
            "Accuracy": 0.8920
        },
        "improvement_ap_pct": 53.8,
        "improvement_auc_delta": 0.0510
    }
}

class EvaluationService:
    """
    Supplies both the research paper benchmark evaluation metrics and the
    local test-set evaluation results for all six ML configurations.
    """

    def __init__(self, results_path: str = "data/results/evaluation_metrics.json"):
        self.results_path = results_path

    def get_research_benchmarks(self) -> Dict[str, Any]:
        """
        Returns the published research paper benchmark evaluation data.
        """
        # Comparison summary formatted for frontend grouped bar charts
        ap_comparison = [
            {
                "model": "Logistic Regression (Primary)",
                "Static_AP": RESEARCH_BENCHMARK_RESULTS["LogisticRegression"]["static"]["Average_Precision"],
                "Combined_AP": RESEARCH_BENCHMARK_RESULTS["LogisticRegression"]["combined"]["Average_Precision"],
                "Improvement": "+36.0%"
            },
            {
                "model": "Random Forest",
                "Static_AP": RESEARCH_BENCHMARK_RESULTS["RandomForest"]["static"]["Average_Precision"],
                "Combined_AP": RESEARCH_BENCHMARK_RESULTS["RandomForest"]["combined"]["Average_Precision"],
                "Improvement": "+53.8%"
            },
            {
                "model": "Decision Tree",
                "Static_AP": RESEARCH_BENCHMARK_RESULTS["DecisionTree"]["static"]["Average_Precision"],
                "Combined_AP": RESEARCH_BENCHMARK_RESULTS["DecisionTree"]["combined"]["Average_Precision"],
                "Improvement": "+17.5%"
            }
        ]

        auc_comparison = [
            {
                "model": "Logistic Regression",
                "Static_AUC": RESEARCH_BENCHMARK_RESULTS["LogisticRegression"]["static"]["ROC_AUC"],
                "Combined_AUC": RESEARCH_BENCHMARK_RESULTS["LogisticRegression"]["combined"]["ROC_AUC"]
            },
            {
                "model": "Random Forest",
                "Static_AUC": RESEARCH_BENCHMARK_RESULTS["RandomForest"]["static"]["ROC_AUC"],
                "Combined_AUC": RESEARCH_BENCHMARK_RESULTS["RandomForest"]["combined"]["ROC_AUC"]
            },
            {
                "model": "Decision Tree",
                "Static_AUC": RESEARCH_BENCHMARK_RESULTS["DecisionTree"]["static"]["ROC_AUC"],
                "Combined_AUC": RESEARCH_BENCHMARK_RESULTS["DecisionTree"]["combined"]["ROC_AUC"]
            }
        ]

        return {
            "disclaimer": (
                "These benchmark figures originate from the rigorous empirical evaluation in the research paper. "
                "They evaluate the models against the historical benchmark defect corpus and demonstrate the "
                "significant boost achieved by integrating Git evolution metrics into static defect predictors."
            ),
            "primary_model": "LogisticRegression_combined",
            "models": RESEARCH_BENCHMARK_RESULTS,
            "chart_data": {
                "ap_comparison": ap_comparison,
                "auc_comparison": auc_comparison
            }
        }

    def get_pipeline_evaluation(self) -> Dict[str, Any]:
        """
        Loads the test set evaluation results from the local pipeline.
        """
        if not os.path.exists(self.results_path):
            return {
                "available": False,
                "message": "Evaluation metrics file not found. Run model evaluation first."
            }

        try:
            with open(self.results_path, "r") as f:
                data = json.load(f)

            # Build comparison table for all 6 configurations
            table = []
            for model_name, modes in data.items():
                for mode, metrics in modes.items():
                    table.append({
                        "model": f"{model_name} ({'Combined' if mode == 'combined' else 'Static Only'})",
                        "model_family": model_name,
                        "configuration": mode,
                        "Accuracy": round(metrics.get("Accuracy", 0), 4),
                        "Precision": round(metrics.get("Precision", 0), 4),
                        "Recall": round(metrics.get("Recall", 0), 4),
                        "F1_Score": round(metrics.get("F1_Score", 0), 4),
                        "ROC_AUC": round(metrics.get("ROC_AUC", 0), 4),
                        "ConfusionMatrix": metrics.get("ConfusionMatrix", [])
                    })

            return {
                "available": True,
                "raw_metrics": data,
                "comparison_table": table
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }

