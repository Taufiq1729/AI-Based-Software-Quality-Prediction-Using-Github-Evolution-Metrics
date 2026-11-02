"""
API Endpoint Test Suite.
Tests:
- GET /
- GET /evaluation
- GET /feature-importance
- POST /predict
- POST /scan-repo (using a local test git repo with real Java files and commits)
"""

import os
import sys
import shutil
import tempfile
import unittest
import subprocess
import joblib
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from api.main import _load_model_and_scaler, _rank_scan_results, _validate_model_input, app
from src.data.feature_extractor import FEATURE_COLUMNS


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_scan_result_ranking_is_deterministic_and_rejects_invalid_scores(self):
        ranked, failures = _rank_scan_results([
            {"file": "zeta.java", "model_score": 0.8},
            {"file": "Beta.java", "model_score": 0.8},
            {"file": "alpha.java", "model_score": 0.9},
            {"file": "invalid.java", "model_score": float("nan")},
            {"file": "missing.java"},
        ])

        self.assertEqual([item["file"] for item in ranked], ["alpha.java", "Beta.java", "zeta.java"])
        self.assertEqual([item["rank"] for item in ranked], [1, 2, 3])
        self.assertEqual(ranked[0]["priority"], "Highest priority")
        self.assertEqual(ranked[1]["model_score"], ranked[2]["model_score"])
        self.assertEqual(ranked[1]["priority"], ranked[2]["priority"])
        self.assertEqual(ranked[1]["score_tie_count"], 2)
        self.assertEqual(
            [failure["file"] for failure in failures],
            ["invalid.java", "missing.java"],
        )

    def test_01_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["feature_count"], 15)
        self.assertEqual(data["supported_features"], FEATURE_COLUMNS)

    def test_02_evaluation_endpoint(self):
        response = self.client.get("/evaluation")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("RandomForest", data)
        self.assertIn("combined", data["RandomForest"])
        self.assertIn("ROC_AUC", data["RandomForest"]["combined"])

    def test_prediction_audit_endpoint(self):
        response = self.client.get("/prediction-audit")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["feature_columns"], FEATURE_COLUMNS)
        self.assertTrue(data["saved_evaluation_metrics_match"])
        self.assertFalse(data["independent_external_repository_labels_available"])
        self.assertEqual(len(data["scanner_feature_distribution"]), 15)
        self.assertEqual(len(data["calibration_bins"]), 10)
        self.assertGreater(
            data["scanner_diagnostics"]["high_score_analysis"]["captured_repository_feature_rows"],
            0,
        )

    def test_03_feature_importance_endpoint(self):
        response = self.client.get("/feature-importance")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 15, "Should return importance for all 15 features")
        features_returned = [item["Feature"] for item in data]
        self.assertEqual(features_returned, FEATURE_COLUMNS)
        self.assertTrue(all("Signed_Coefficient" in item for item in data))
        self.assertTrue(all("Absolute_Coefficient" in item for item in data))

        model = joblib.load(os.path.join(
            project_root,
            "src",
            "models",
            "saved",
            "LogisticRegression_combined.pkl",
        ))
        for index, item in enumerate(data):
            self.assertAlmostEqual(item["Signed_Coefficient"], model.coef_[0][index])
            self.assertAlmostEqual(item["Absolute_Coefficient"], abs(model.coef_[0][index]))

    def test_04_predict_endpoint(self):
        payload = {
            "LOC": 150.0, "WMC": 10.0, "DIT": 2.0, "NOC": 0.0, "RFC": 20.0,
            "LCOM5": 0.4, "CBO": 6.0, "NPA": 1.0, "NPM": 5.0, "NLE": 2.0,
            "CBOI": 2.0, "CD": 0.12,
            "code_churn": 60.0, "revision_count": 8.0, "developer_count": 3.0
        }
        response = self.client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("probability", data)
        self.assertIn("model_score", data)
        self.assertIn("risk_level", data)
        self.assertIn("prediction", data)
        self.assertIn(data["risk_level"], ["HIGH", "LOW"])

        model = joblib.load(os.path.join(
            project_root,
            "src",
            "models",
            "saved",
            "LogisticRegression_combined.pkl",
        ))
        scaler = joblib.load(os.path.join(project_root, "data", "processed", "scaler.pkl"))
        features = pd.DataFrame([payload], columns=FEATURE_COLUMNS)
        scaled_features = pd.DataFrame(scaler.transform(features), columns=FEATURE_COLUMNS)
        positive_class_index = list(model.classes_).index(1)
        expected_probability = model.predict_proba(scaled_features)[0][positive_class_index]
        self.assertAlmostEqual(data["probability"], expected_probability)
        self.assertAlmostEqual(data["model_score"], expected_probability)
        self.assertEqual(data["prediction"], int(model.predict(scaled_features)[0]))
        self.assertEqual(data["risk_level"], "HIGH" if data["prediction"] == 1 else "LOW")
        self.assertEqual(data["probability_interpretation"], "uncalibrated_model_estimate")

    def test_predict_matches_offline_held_out_record_and_imputes_missing(self):
        model, scaler, medians = _load_model_and_scaler()
        X_test = pd.read_csv(os.path.join(project_root, "data", "processed", "X_test.csv"))[FEATURE_COLUMNS]
        y_test = pd.read_csv(os.path.join(project_root, "data", "processed", "y_test.csv")).iloc[:, 0]
        raw_test = pd.DataFrame(scaler.inverse_transform(X_test), columns=FEATURE_COLUMNS)
        row_index = int(y_test[y_test == 1].index[0])
        payload = raw_test.iloc[row_index].to_dict()

        response = self.client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 200)

        offline_probability = model.predict_proba(X_test.iloc[[row_index]])[
            0, list(model.classes_).index(1)
        ]
        offline_prediction = int(model.predict(X_test.iloc[[row_index]])[0])
        self.assertAlmostEqual(response.json()["probability"], offline_probability, places=12)
        self.assertEqual(response.json()["prediction"], offline_prediction)

        raw_with_missing = raw_test.iloc[[row_index]].copy()
        raw_with_missing.iloc[0, 0] = np.nan
        prepared = _validate_model_input(raw_with_missing, scaler, medians)
        expected = pd.DataFrame(
            scaler.transform(raw_with_missing.fillna(medians)),
            columns=FEATURE_COLUMNS,
        )
        self.assertTrue(np.allclose(prepared, expected))
        self.assertTrue(np.isfinite(prepared.to_numpy()).all())

    def test_05_scan_repo_local_test(self):
        """Tests /scan-repo on a real local git repository with Java code."""
        temp_repo = tempfile.mkdtemp(prefix="api_test_scan_repo_")
        try:
            subprocess.run(["git", "init"], cwd=temp_repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=temp_repo, check=True)
            subprocess.run(["git", "config", "user.email", "tester@sqam.com"], cwd=temp_repo, check=True)

            code = '''
package com.demo;
public class DemoService {
    public int counter = 0;
    public void increment() {
        if (counter < 10) {
            counter++;
        }
    }
}
'''
            java_file = os.path.join(temp_repo, "DemoService.java")
            with open(java_file, "w") as f:
                f.write(code)

            subprocess.run(["git", "add", "DemoService.java"], cwd=temp_repo, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_repo, check=True)

            # File URI as repo URL for git.Repo.clone_from
            repo_file_url = "file:///" + temp_repo.replace("\\", "/")
            response = self.client.post("/scan-repo?limit=1", json={"url": repo_file_url})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("files", data)
            self.assertEqual(data["repository_commit"], subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=temp_repo, check=True,
                capture_output=True, text=True
            ).stdout.strip())
            self.assertEqual(data["java_files_discovered"], 1)
            self.assertEqual(data["files_analyzed"], 1)
            self.assertEqual(data["files_scored"], 1)
            self.assertEqual(data["files_returned"], 1)
            self.assertEqual(data["result_limit"], 1)
            self.assertEqual(data["classes_discovered"], 1)
            self.assertEqual(data["classes_scored"], 1)
            self.assertEqual(data["non_primary_classes_not_scored"], 0)
            self.assertEqual(data["unidentified_class_file_count"], 0)
            self.assertEqual(data["context_parse_failures"], [])
            self.assertEqual(data["analysis_failures"], [])
            self.assertEqual(len(data["files"]), 1)
            file_res = data["files"][0]
            self.assertEqual(file_res["rank"], 1)
            self.assertEqual(file_res["priority"], "Highest priority")
            self.assertEqual(file_res["file"], "DemoService.java")
            self.assertEqual(file_res["class_name"], "DemoService")
            self.assertEqual(file_res["class_identity"], "com.demo.DemoService")
            self.assertGreater(file_res["loc"], 0)
            self.assertGreaterEqual(file_res["revisions"], 1)
            self.assertGreater(file_res["churn"], 0)
            self.assertIn("metrics", file_res)
            self.assertEqual(len(file_res["metrics"]), 15)

            model = joblib.load(os.path.join(
                project_root,
                "src",
                "models",
                "saved",
                "LogisticRegression_combined.pkl",
            ))
            scaler = joblib.load(os.path.join(project_root, "data", "processed", "scaler.pkl"))
            features = pd.DataFrame([file_res["metrics"]], columns=FEATURE_COLUMNS)
            scaled_features = pd.DataFrame(scaler.transform(features), columns=FEATURE_COLUMNS)
            positive_class_index = list(model.classes_).index(1)
            expected_probability = model.predict_proba(scaled_features)[0][positive_class_index]
            expected_prediction = int(model.predict(scaled_features)[0])
            self.assertAlmostEqual(file_res["risk_probability"], expected_probability)
            self.assertAlmostEqual(file_res["model_score"], expected_probability)
            self.assertEqual(file_res["risk_level"], "HIGH" if expected_prediction == 1 else "LOW")
            self.assertEqual(data["probability_interpretation"], "uncalibrated_model_estimate")

            all_response = self.client.post("/scan-repo?limit=0", json={"url": repo_file_url})
            self.assertEqual(all_response.status_code, 200)
            self.assertEqual(all_response.json()["files_returned"], all_response.json()["files_scored"])
            self.assertIsNone(all_response.json()["result_limit"])
        finally:
            shutil.rmtree(temp_repo, ignore_errors=True)

    def test_scan_repo_handles_empty_invalid_clone_and_unsupported_syntax(self):
        invalid = self.client.post("/scan-repo", json={"url": "not-a-repository-url"})
        self.assertEqual(invalid.status_code, 400)

        missing_path = os.path.join(tempfile.gettempdir(), "sqam-missing-repo-for-test")
        missing_url = "file:///" + missing_path.replace("\\", "/").lstrip("/")
        clone_failure = self.client.post("/scan-repo", json={"url": missing_url})
        self.assertEqual(clone_failure.status_code, 400)

        empty_repo = tempfile.mkdtemp(prefix="api_test_empty_repo_")
        unsupported_repo = tempfile.mkdtemp(prefix="api_test_unsupported_java_")
        try:
            subprocess.run(["git", "init"], cwd=empty_repo, check=True, capture_output=True)
            empty_url = "file:///" + empty_repo.replace("\\", "/").lstrip("/")
            empty_response = self.client.post("/scan-repo", json={"url": empty_url})
            self.assertEqual(empty_response.status_code, 200)
            self.assertEqual(empty_response.json()["files"], [])
            self.assertEqual(empty_response.json()["files_returned"], 0)
            self.assertEqual(empty_response.json()["files_analyzed"], 0)
            self.assertIsNone(empty_response.json()["repository_commit"])

            subprocess.run(["git", "init"], cwd=unsupported_repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Syntax Tester"], cwd=unsupported_repo, check=True)
            subprocess.run(["git", "config", "user.email", "syntax@example.test"], cwd=unsupported_repo, check=True)
            source = "package sample; public record ModernRecord(String value) {}\n"
            with open(os.path.join(unsupported_repo, "ModernRecord.java"), "w", encoding="utf-8") as stream:
                stream.write(source)
            subprocess.run(["git", "add", "ModernRecord.java"], cwd=unsupported_repo, check=True)
            subprocess.run(["git", "commit", "-m", "Add record"], cwd=unsupported_repo, check=True, capture_output=True)

            unsupported_url = "file:///" + unsupported_repo.replace("\\", "/").lstrip("/")
            unsupported_response = self.client.post("/scan-repo", json={"url": unsupported_url})
            self.assertEqual(unsupported_response.status_code, 200)
            unsupported_data = unsupported_response.json()
            self.assertEqual(unsupported_data["files_scored"], 1)
            self.assertEqual(unsupported_data["classes_scored"], 0)
            self.assertEqual(unsupported_data["unidentified_class_file_count"], 1)
            self.assertIn("ModernRecord.java", unsupported_data["unidentified_class_files"][0]["file"])
            self.assertEqual(len(unsupported_data["context_parse_failures"]), 1)
            file_result = unsupported_data["files"][0]
            self.assertGreater(file_result["metrics"]["LOC"], 0)
            self.assertGreater(file_result["metrics"]["revision_count"], 0)
            self.assertGreaterEqual(file_result["risk_probability"], 0.0)
            self.assertLessEqual(file_result["risk_probability"], 1.0)
            self.assertEqual(len(file_result["metrics"]), 15)
        finally:
            shutil.rmtree(empty_repo, ignore_errors=True)
            shutil.rmtree(unsupported_repo, ignore_errors=True)



if __name__ == "__main__":
    unittest.main()
