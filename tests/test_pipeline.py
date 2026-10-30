"""
Comprehensive Test Suite for Java Quality Prediction Pipeline.
Validates:
1. Static metrics generated from historical JUnit source files.
2. Correct class-to-file mapping for multi-class and nested files.
3. Whole-project inheritance and coupling relationships.
4. Training/scanning feature parity (exact parity across all 15 features).
5. Release-based train/test separation (strict temporal validity, no leakage).
6. No future Git commits included in historical features (lookahead prevention).
7. Git rename tracking across file moves and renames.
8. Reproducibility of Git evolution metrics.
9. Saved model and preprocessing compatibility.
10. End-to-end repository scan and prediction via /scan-repo API.
"""

import os
import sys
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from fastapi.testclient import TestClient

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from api.main import app
from src.analyzers.java_analyzer import (
    analyze_java_file,
    analyze_java_source,
    build_repository_context,
    find_class_line_range
)
from src.data.git_miner import (
    mine_file_history,
    mine_repository_evolution,
    _normalize_path
)
from src.data.feature_extractor import (
    FEATURE_COLUMNS,
    STATIC_FEATURES,
    EVOLUTION_FEATURES,
    validate_feature_vector,
    extract_file_features,
    extract_repository_features
)
from src.data.preprocessing import TRAIN_RELEASE_COMMITS, TEST_RELEASE_COMMITS
from src.models.train import make_release_time_splits
from src.models.evaluate import _evaluate_predictions


class TestJavaPipelineAudit(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.sample_code = """package com.demo;

import java.io.IOException;
import java.util.List;

public class CalculatorService extends BaseCalculator {
    public int executionCount = 0;
    public String name = "Calc";
    private double lastResult = 0.0;

    public double compute(int a, int b) throws IOException {
        if (a < 0 || b < 0) {
            throw new IllegalArgumentException("Negative numbers not allowed");
        }
        for (int i = 0; i < b; i++) {
            if (i % 2 == 0) {
                executionCount++;
                recordStep();
            }
        }
        lastResult = a + b;
        return lastResult;
    }

    public void recordStep() {
        executionCount++;
    }
}
"""

    def test_01_static_analyzer(self):
        """Test 1: Static AST analyzer produces all 12 contract metrics accurately."""
        with tempfile.NamedTemporaryFile(suffix=".java", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(self.sample_code)
            tmp_path = tmp.name

        try:
            metrics = analyze_java_file(tmp_path)
            self.assertEqual(len(metrics), 12, "Must return exactly 12 static metrics")

            for col in STATIC_FEATURES:
                self.assertIn(col, metrics, f"Metric '{col}' must be present")
                self.assertIsInstance(metrics[col], (int, float), f"Metric '{col}' must be numeric")

            self.assertEqual(metrics["NPA"], 2.0, "Expected 2 public attributes (executionCount, name)")
            self.assertEqual(metrics["NPM"], 2.0, "Expected 2 public methods (compute, recordStep)")
            self.assertEqual(metrics["DIT"], 1.0, "Expected DIT 1 (extends BaseCalculator)")
            self.assertGreater(metrics["LOC"], 20, "LOC should be > 20")
            self.assertGreater(metrics["WMC"], 1, "WMC should include branches")
            self.assertGreater(metrics["RFC"], 2, "RFC should include declared and invoked methods/constructors")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_02_historical_source_static_metrics(self):
        """Test 2: Static metrics generated from historical JUnit source files."""
        repo_git = os.path.join(project_root, "data/repos/junit4.git")
        self.assertTrue(os.path.exists(repo_git), "JUnit 4 bare repository mirror must exist")

        # Extract ActiveTestSuite.java directly from historical commit 64155f8a9babcfcf4263cf4d08253a1556e75481
        commit = "64155f8a9babcfcf4263cf4d08253a1556e75481"
        file_path = "src/main/java/junit/extensions/ActiveTestSuite.java"

        cmd = ["git", f"--git-dir={repo_git}", "show", f"{commit}:{file_path}"]
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        self.assertEqual(proc.returncode, 0, f"Git show failed: {proc.stderr}")

        content = proc.stdout
        metrics = analyze_java_source(content, target_class_name="ActiveTestSuite")

        self.assertEqual(len(metrics), 12)
        self.assertGreater(metrics["LOC"], 10)
        self.assertGreater(metrics["WMC"], 0)
        self.assertGreater(metrics["NPM"], 0)
        self.assertIsInstance(metrics["LCOM5"], float)

    def test_03_class_to_file_mapping(self):
        """Test 3: Correct class-to-file mapping for multi-class and nested files."""
        multi_class_code = """package org.junit;

public class OuterClass {
    public int outerField;
    public void outerMethod() {}

    public static class InnerMember {
        public int innerField;
        public void innerMethod() {}
    }
}
"""
        with tempfile.NamedTemporaryFile(suffix=".java", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(multi_class_code)
            tmp_path = tmp.name

        try:
            # Outer class range
            sl_outer, el_outer = find_class_line_range(multi_class_code, 3)
            self.assertEqual(sl_outer, 3)
            self.assertEqual(el_outer, 11)

            # Inner class range
            sl_inner, el_inner = find_class_line_range(multi_class_code, 7)
            self.assertEqual(sl_inner, 7)
            self.assertEqual(el_inner, 10)

            # Analyze outer class
            outer_metrics = analyze_java_source(multi_class_code, target_class_name="OuterClass", line_range=(3, 11))
            self.assertEqual(outer_metrics["LOC"], 9.0)
            self.assertEqual(outer_metrics["NPA"], 1.0)
            self.assertEqual(outer_metrics["NPM"], 1.0)

            # Analyze inner class
            inner_metrics = analyze_java_source(multi_class_code, target_class_name="InnerMember", line_range=(7, 10))
            self.assertEqual(inner_metrics["LOC"], 4.0)
            self.assertEqual(inner_metrics["NPA"], 1.0)
            self.assertEqual(inner_metrics["NPM"], 1.0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_nested_target_name_disambiguates_tied_line_range(self):
        temp_dir = tempfile.mkdtemp(prefix="test_nested_identity_line_")
        source_path = Path(temp_dir, "sample", "Outer.java")
        source_path.parent.mkdir(parents=True)
        nested_code = """package sample;
public class Base {}




public class Outer extends Base {
    public void outerMethod() {}
    public class Inner extends Base {
        public void firstInnerMethod() {}
        public void secondInnerMethod() {}
    }
}
class OuterChildOne extends Outer {}
class OuterChildTwo extends Outer {}
class InnerChild extends Outer.Inner {}
"""
        source_path.write_text(nested_code, encoding="utf-8")
        try:
            context = build_repository_context(temp_dir)
            metrics = analyze_java_source(
                nested_code,
                target_class_name="Outer$Inner",
                line_range=(8, 11),
                relative_path="sample/Outer.java",
                project_context=context,
            )
            self.assertEqual(metrics["NOC"], 1.0)
            self.assertEqual(metrics["NPM"], 1.0)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_04_whole_project_inheritance_and_coupling(self):
        """Test 4: Whole-project inheritance and coupling calculation."""
        temp_dir = tempfile.mkdtemp(prefix="test_proj_context_")
        try:
            # Create a 3-tier class hierarchy across multiple files
            # GrandParent.java
            with open(os.path.join(temp_dir, "GrandParent.java"), "w") as f:
                f.write("public class GrandParent { public void gpMethod() {} }\n")

            # Parent.java
            with open(os.path.join(temp_dir, "Parent.java"), "w") as f:
                f.write("public class Parent extends GrandParent { public void pMethod() {} }\n")

            # Child.java
            with open(os.path.join(temp_dir, "Child.java"), "w") as f:
                f.write("public class Child extends Parent { public void cMethod() {} }\n")

            # Caller.java (references GrandParent)
            with open(os.path.join(temp_dir, "Caller.java"), "w") as f:
                f.write("public class Caller { public GrandParent gp; }\n")

            context = build_repository_context(temp_dir)

            child_metrics = analyze_java_file(os.path.join(temp_dir, "Child.java"), project_context=context)
            gp_metrics = analyze_java_file(os.path.join(temp_dir, "GrandParent.java"), project_context=context)

            # Child: extends Parent (1) which extends GrandParent (2) -> DIT = 2
            self.assertEqual(child_metrics["DIT"], 2.0, "Child DIT should be 2")
            # GrandParent has at least 1 subclass (Parent) -> NOC = 1
            self.assertEqual(gp_metrics["NOC"], 1.0, "GrandParent NOC should be 1")
            # Caller references GrandParent -> CBOI > 0
            self.assertGreaterEqual(gp_metrics["CBOI"], 1.0, "GrandParent inward coupling should be >= 1")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_qualified_class_identity_for_inheritance_and_coupling(self):
        temp_dir = tempfile.mkdtemp(prefix="test_qualified_identity_")
        sources = {
            "a/Base.java": "package a; public class Base {}\n",
            "a/Child.java": "package a; public class Child extends Base {}\n",
            "a/Caller.java": "package a; public class Caller { Base value; }\n",
            "a/Outer.java": "package a; public class Outer { public static class NestedBase {} }\n",
            "a/NestedCaller.java": "package a; public class NestedCaller { Outer.NestedBase value; }\n",
            "b/Base.java": "package b; public class Base {}\n",
            "b/Child.java": "package b; public class Child extends Base {}\n",
            "b/Caller.java": "package b; public class Caller { Base value; }\n",
            "c/NestedBase.java": "package c; public class NestedBase {}\n",
            "c/ImportedA.java": "package c; import a.Base; public class ImportedA extends Base {}\n",
            "c/ImportedB.java": "package c; import b.Base; public class ImportedB extends Base {}\n",
            "c/Ambiguous.java": "package c; import a.*; import b.*; public class Ambiguous extends Base {}\n",
            "c/NestedChild.java": "package c; import a.Outer.NestedBase; public class NestedChild extends NestedBase {}\n",
            "c/FullyQualifiedNestedCaller.java": "package c; public class FullyQualifiedNestedCaller { a.Outer.NestedBase value; }\n",
        }
        try:
            for relative_path, source in sources.items():
                full_path = Path(temp_dir, relative_path)
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(source, encoding="utf-8")

            context = build_repository_context(temp_dir)
            base_a = analyze_java_file(os.path.join(temp_dir, "a/Base.java"), project_context=context)
            base_b = analyze_java_file(os.path.join(temp_dir, "b/Base.java"), project_context=context)
            nested_base = analyze_java_file(
                os.path.join(temp_dir, "a/Outer.java"),
                target_class_name="NestedBase",
                project_context=context,
            )
            unrelated_nested_base = analyze_java_file(
                os.path.join(temp_dir, "c/NestedBase.java"), project_context=context
            )

            self.assertEqual(base_a["NOC"], 2.0)
            self.assertEqual(base_b["NOC"], 2.0)
            self.assertEqual(base_a["CBOI"], 3.0)
            self.assertEqual(base_b["CBOI"], 3.0)
            self.assertEqual(nested_base["NOC"], 1.0)
            self.assertEqual(nested_base["CBOI"], 3.0)
            self.assertEqual(unrelated_nested_base["CBOI"], 0.0)
            self.assertIn("a.Outer.NestedBase", context["class_to_file"])

            ambiguous = [
                entry for entry in context["unresolved_references"]
                if entry["source_class_id"] == "c.Ambiguous"
                and entry["reference"] == "Base"
            ]
            self.assertEqual(len(ambiguous), 1)
            self.assertEqual(ambiguous[0]["resolution"], "ambiguous")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_05_training_scanning_feature_parity(self):
        """Test 5: Training and scanning paths produce 100% identical features for the same source file."""
        repo_git = os.path.join(project_root, "data/repos/junit4.git")
        temp_scan_dir = tempfile.mkdtemp(prefix="test_parity_")
        try:
            # Clone and checkout commit 64155f8a9babcfcf4263cf4d08253a1556e75481
            commit = "64155f8a9babcfcf4263cf4d08253a1556e75481"
            subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", repo_git, temp_scan_dir], check=True)
            subprocess.run(["git", "-C", temp_scan_dir, "checkout", "--quiet", "--detach", commit], check=True)

            target_rel = "src/main/java/junit/extensions/ActiveTestSuite.java"
            target_abs = os.path.join(temp_scan_dir, target_rel)
            self.assertTrue(os.path.exists(target_abs))

            # 1. Scanning path: extract_repository_features
            repo_df = extract_repository_features(temp_scan_dir)
            matched = repo_df[repo_df["file"] == target_rel.replace("\\", "/")]
            self.assertEqual(len(matched), 1, "Expected target file in repository scan results")
            scan_features = matched.iloc[0][FEATURE_COLUMNS].to_dict()

            # 2. Training path: extract_file_features
            context = build_repository_context(temp_scan_dir)
            train_features = extract_file_features(
                file_path=target_abs,
                repo_path=temp_scan_dir,
                project_context=context,
                to_commit=commit
            )

            # Compare all 15 features - must have 100% exact parity
            for col in FEATURE_COLUMNS:
                scan_val = float(scan_features[col])
                train_val = float(train_features[col])
                self.assertAlmostEqual(
                    scan_val, train_val, places=4,
                    msg=f"Parity mismatch on {col}: scan={scan_val}, train={train_val}"
                )
        finally:
            shutil.rmtree(temp_scan_dir, ignore_errors=True)

    def test_06_release_based_train_test_separation(self):
        """Test 6: Release-based train/test separation strictly respects chronological order."""
        repo_git = os.path.join(project_root, "data/repos/junit4.git")

        # Get commit timestamps
        train_dates = []
        for c in TRAIN_RELEASE_COMMITS:
            p = subprocess.run(["git", f"--git-dir={repo_git}", "log", "-1", "--format=%cI", c],
                               capture_output=True, text=True, check=True)
            train_dates.append((c, p.stdout.strip()))

        test_dates = []
        for c in TEST_RELEASE_COMMITS:
            p = subprocess.run(["git", f"--git-dir={repo_git}", "log", "-1", "--format=%cI", c],
                               capture_output=True, text=True, check=True)
            test_dates.append((c, p.stdout.strip()))

        max_train_date = max(d for _, d in train_dates)
        min_test_date = min(d for _, d in test_dates)

        self.assertLess(
            max_train_date, min_test_date,
            f"Temporal leakage detected: max train date {max_train_date} is not before min test date {min_test_date}"
        )

        # Disjoint commit sets
        overlap = set(TRAIN_RELEASE_COMMITS).intersection(set(TEST_RELEASE_COMMITS))
        self.assertEqual(len(overlap), 0, f"Overlapping commits found between train and test: {overlap}")

    def test_release_cross_validation_holds_out_whole_releases(self):
        groups = pd.read_csv(os.path.join(project_root, "data/processed/train_release_groups.csv"))["release_commit"]
        release_order = groups.drop_duplicates().tolist()

        splits = make_release_time_splits(groups)

        self.assertEqual(len(splits), len(release_order) - 1)
        for position, (train_indices, validation_indices) in enumerate(splits, start=1):
            train_releases = set(groups.iloc[train_indices])
            validation_releases = set(groups.iloc[validation_indices])
            self.assertEqual(train_releases, set(release_order[:position]))
            self.assertEqual(validation_releases, {release_order[position]})
            self.assertTrue(train_releases.isdisjoint(validation_releases))

    def test_average_precision_is_primary_pr_auc_and_one_class_is_undefined(self):
        labels = np.array([0, 0, 1])
        predictions = np.zeros(3, dtype=int)
        probabilities = np.zeros(3, dtype=float)

        metrics = _evaluate_predictions(labels, predictions, probabilities)

        self.assertAlmostEqual(metrics["PR_AUC"], 1.0 / 3.0)
        self.assertAlmostEqual(metrics["Average_Precision"], 1.0 / 3.0)
        self.assertAlmostEqual(metrics["PR_AUC_trapezoidal"], 2.0 / 3.0)

        no_positive = _evaluate_predictions(
            np.zeros(3, dtype=int), predictions, probabilities
        )
        self.assertIsNone(no_positive["PR_AUC"])
        self.assertIsNone(no_positive["PR_AUC_trapezoidal"])
        self.assertIsNone(no_positive["ROC_AUC"])
        self.assertIsNone(no_positive["PR_Curve"])

    def test_07_no_future_git_commits_in_historical_features(self):
        """Test 7: No future Git commits included in historical evolution metrics."""
        temp_repo = tempfile.mkdtemp(prefix="test_lookahead_")
        try:
            subprocess.run(["git", "init"], cwd=temp_repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Dev"], cwd=temp_repo, check=True)
            subprocess.run(["git", "config", "user.email", "dev@test.com"], cwd=temp_repo, check=True)

            fpath = os.path.join(temp_repo, "TestClass.java")

            # Commit 1 (historical release)
            with open(fpath, "w") as f:
                f.write("public class TestClass { int v1 = 1; }\n")
            subprocess.run(["git", "add", "TestClass.java"], cwd=temp_repo, check=True)
            subprocess.run(["git", "commit", "-m", "Commit 1"], cwd=temp_repo, check=True)
            p1 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=temp_repo, capture_output=True, text=True, check=True)
            c1 = p1.stdout.strip()

            # Commit 2 (future commit)
            with open(fpath, "a") as f:
                f.write("public void futureMethod() {}\n")
            subprocess.run(["git", "add", "TestClass.java"], cwd=temp_repo, check=True)
            subprocess.run(["git", "commit", "-m", "Commit 2 - Future"], cwd=temp_repo, check=True)

            # Mine history up to historical commit 1
            hist_stats = mine_file_history(temp_repo, "TestClass.java", to_commit=c1)
            future_stats = mine_file_history(temp_repo, "TestClass.java")

            self.assertEqual(hist_stats["revision_count"], 1, "Historical mining must see exactly 1 revision")
            self.assertEqual(future_stats["revision_count"], 2, "Latest mining must see 2 revisions")
            self.assertLess(hist_stats["code_churn"], future_stats["code_churn"], "Historical churn must exclude future additions")
        finally:
            shutil.rmtree(temp_repo, ignore_errors=True)

    def test_08_git_rename_tracking(self):
        """Test 8: Git evolution mining follows file history across renames and moves."""
        temp_repo = tempfile.mkdtemp(prefix="test_rename_")
        try:
            subprocess.run(["git", "init"], cwd=temp_repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "DevOne"], cwd=temp_repo, check=True)
            subprocess.run(["git", "config", "user.email", "dev1@test.com"], cwd=temp_repo, check=True)

            # Commit 1: OldFile.java
            with open(os.path.join(temp_repo, "OldFile.java"), "w") as f:
                f.write("\n".join([f"line {i}" for i in range(20)]) + "\n")
            subprocess.run(["git", "add", "OldFile.java"], cwd=temp_repo, check=True)
            subprocess.run(["git", "commit", "-m", "Initial file commit"], cwd=temp_repo, check=True)

            # Commit 2: Rename OldFile.java -> NewFile.java by DevTwo
            subprocess.run(["git", "config", "user.name", "DevTwo"], cwd=temp_repo, check=True)
            subprocess.run(["git", "config", "user.email", "dev2@test.com"], cwd=temp_repo, check=True)
            subprocess.run(["git", "mv", "OldFile.java", "NewFile.java"], cwd=temp_repo, check=True)
            with open(os.path.join(temp_repo, "NewFile.java"), "a") as f:
                f.write("new line 21\nnew line 22\n")
            subprocess.run(["git", "add", "NewFile.java"], cwd=temp_repo, check=True)
            subprocess.run(["git", "commit", "-m", "Rename to NewFile.java"], cwd=temp_repo, check=True)

            # Mine NewFile.java
            stats = mine_file_history(temp_repo, "NewFile.java")

            self.assertEqual(stats["revision_count"], 2, "Expected 2 revisions across the rename")
            self.assertEqual(stats["developer_count"], 2, "Expected 2 developers across the rename")
            self.assertGreater(stats["code_churn"], 20, "Expected churn to include pre-rename lines")
        finally:
            shutil.rmtree(temp_repo, ignore_errors=True)

    def test_09_evolution_metrics_reproducibility(self):
        """Test 9: Evolution metrics mining is 100% deterministic and reproducible."""
        repo_git = os.path.join(project_root, "data/repos/junit4.git")
        commit = "64155f8a9babcfcf4263cf4d08253a1556e75481"
        target_file = "src/main/java/junit/extensions/ActiveTestSuite.java"

        run1 = mine_file_history(repo_git, target_file, to_commit=commit)
        run2 = mine_file_history(repo_git, target_file, to_commit=commit)

        self.assertEqual(run1["code_churn"], run2["code_churn"])
        self.assertEqual(run1["revision_count"], run2["revision_count"])
        self.assertEqual(run1["developer_count"], run2["developer_count"])

    def test_10_saved_model_and_scan_repo_prediction(self):
        """Test 10: Model prediction and end-to-end /scan-repo API endpoint."""
        model_path = os.path.join(project_root, "src/models/saved/RandomForest_combined.pkl")
        scaler_path = os.path.join(project_root, "data/processed/scaler.pkl")

        if os.path.exists(model_path) and os.path.exists(scaler_path):
            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)

            sample_input = {col: 1.0 for col in FEATURE_COLUMNS}
            df_input = validate_feature_vector(sample_input)
            scaled = scaler.transform(df_input)
            prob = float(model.predict_proba(scaled)[0][1])
            self.assertTrue(0.0 <= prob <= 1.0)

        # Test /scan-repo API endpoint on local temporary git repository
        temp_repo = tempfile.mkdtemp(prefix="api_test_scan_")
        try:
            subprocess.run(["git", "init"], cwd=temp_repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=temp_repo, check=True)
            subprocess.run(["git", "config", "user.email", "tester@test.com"], cwd=temp_repo, check=True)

            code = "public class SampleTest { public void testMethod() {} }\n"
            with open(os.path.join(temp_repo, "SampleTest.java"), "w") as f:
                f.write(code)
            subprocess.run(["git", "add", "SampleTest.java"], cwd=temp_repo, check=True)
            subprocess.run(["git", "commit", "-m", "Init"], cwd=temp_repo, check=True)

            file_url = "file:///" + temp_repo.replace("\\", "/")
            res = self.client.post("/scan-repo", json={"url": file_url})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("files", data)
            self.assertEqual(data["total_java_files_analyzed"], 1)
            self.assertEqual(len(data["files"]), 1)
            first_file = data["files"][0]
            self.assertIn("risk_probability", first_file)
            self.assertIn("metrics", first_file)
            self.assertEqual(len(first_file["metrics"]), 15)
        finally:
            shutil.rmtree(temp_repo, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
