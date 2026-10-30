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
from fastapi.testclient import TestClient

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from api.main import app
from src.data.feature_extractor import FEATURE_COLUMNS


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

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

    def test_03_feature_importance_endpoint(self):
        response = self.client.get("/feature-importance")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 15, "Should return importance for all 15 features")
        features_returned = [item["Feature"] for item in data]
        for col in FEATURE_COLUMNS:
            self.assertIn(col, features_returned)

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
        self.assertIn("risk_level", data)
        self.assertIn("prediction", data)
        self.assertIn(data["risk_level"], ["HIGH", "LOW"])

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
            response = self.client.post("/scan-repo", json={"url": repo_file_url})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("files", data)
            self.assertEqual(data["repository_commit"], subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=temp_repo, check=True,
                capture_output=True, text=True
            ).stdout.strip())
            self.assertEqual(data["java_files_discovered"], 1)
            self.assertEqual(data["classes_discovered"], 1)
            self.assertEqual(data["classes_scored"], 1)
            self.assertEqual(data["non_primary_classes_not_scored"], 0)
            self.assertEqual(data["unidentified_class_file_count"], 0)
            self.assertEqual(data["context_parse_failures"], [])
            self.assertEqual(data["analysis_failures"], [])
            self.assertEqual(len(data["files"]), 1)
            file_res = data["files"][0]
            self.assertEqual(file_res["file"], "DemoService.java")
            self.assertEqual(file_res["class_name"], "DemoService")
            self.assertEqual(file_res["class_identity"], "com.demo.DemoService")
            self.assertGreater(file_res["loc"], 0)
            self.assertGreaterEqual(file_res["revisions"], 1)
            self.assertGreater(file_res["churn"], 0)
            self.assertIn("metrics", file_res)
            self.assertEqual(len(file_res["metrics"]), 15)
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
