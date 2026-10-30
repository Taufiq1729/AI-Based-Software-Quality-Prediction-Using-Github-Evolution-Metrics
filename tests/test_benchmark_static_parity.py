"""Diagnostic comparison of benchmark metrics with metrics from real source."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.analyzers.java_analyzer import analyze_java_file, build_repository_context
from src.data.feature_extractor import STATIC_FEATURES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_COMMIT = "64155f8a9babcfcf4263cf4d08253a1556e75481"


def _source_relative_path(dataset_path: str) -> str:
    normalized = dataset_path.replace("\\", "/")
    marker = "/src/"
    index = normalized.find(marker)
    if index < 0:
        raise ValueError(f"Dataset path does not identify a source file: {dataset_path}")
    return normalized[index + 1:]


class BenchmarkStaticMetricParityTest(unittest.TestCase):
    def test_reports_metrics_for_ten_release_matched_files(self):
        dataset_path = PROJECT_ROOT / "data/raw/dataset/junit4" / f"dataset-{RELEASE_COMMIT}.csv"
        regenerated_path = PROJECT_ROOT / "data/derived/junit4_regenerated" / f"dataset-{RELEASE_COMMIT}.csv"
        mirror_path = PROJECT_ROOT / "data/repos/junit4.git"
        self.assertTrue(dataset_path.is_file(), f"Missing benchmark CSV: {dataset_path}")
        self.assertTrue(regenerated_path.is_file(), f"Missing regenerated CSV: {regenerated_path}")
        self.assertTrue(mirror_path.is_dir(), f"Missing local Git mirror: {mirror_path}")

        checkout = Path(tempfile.mkdtemp(prefix="sqam-static-parity-"))
        shutil.rmtree(checkout)
        try:
            subprocess.run(
                ["git", "clone", "--quiet", "--no-hardlinks", str(mirror_path), str(checkout)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(checkout), "checkout", "--quiet", "--detach", RELEASE_COMMIT],
                check=True,
                capture_output=True,
                text=True,
            )

            dataset = pd.read_csv(dataset_path)
            regenerated_dataset = pd.read_csv(regenerated_path).set_index("ID")
            context = build_repository_context(str(checkout))
            representatives = []
            seen_paths = set()
            seen_packages = set()
            for _, row in dataset.iterrows():
                relative_path = _source_relative_path(str(row["Path"]))
                source_file = checkout / relative_path
                package = str(Path(relative_path).parent)
                if not source_file.is_file() or relative_path in seen_paths or package in seen_packages:
                    continue
                representatives.append((row, relative_path, source_file))
                seen_paths.add(relative_path)
                seen_packages.add(package)
                if len(representatives) == 10:
                    break

            self.assertEqual(len(representatives), 10, "Expected ten distinct packages with source matches")
            print("Release|Class|Source|Metric|Dataset Value|Analyzer Value|Difference")
            for row, relative_path, source_file in representatives:
                analyzer_metrics = analyze_java_file(str(source_file), project_context=context)
                class_line = int(row["Line"]) if pd.notnull(row.get("Line")) else 1
                class_end_line = int(row["EndLine"]) if pd.notnull(row.get("EndLine")) else class_line
                regenerated_metrics = analyze_java_file(
                    str(source_file),
                    target_class_name=str(row["Name"]),
                    line_range=(class_line, class_end_line),
                    project_context=context,
                )
                generated_row = regenerated_dataset.loc[row["ID"]]
                for metric in STATIC_FEATURES:
                    dataset_value = float(row[metric])
                    analyzer_value = float(analyzer_metrics[metric])
                    self.assertAlmostEqual(
                        float(generated_row[metric]),
                        float(regenerated_metrics[metric]),
                        places=5,
                        msg=f"Regenerated {metric} differs from analyzer for {row['ID']}",
                    )
                    print(
                        f"{RELEASE_COMMIT}|{row['Name']}|{relative_path}|{metric}|"
                        f"{dataset_value:.8g}|{analyzer_value:.8g}|"
                        f"{analyzer_value - dataset_value:.8g}"
                    )
        finally:
            shutil.rmtree(checkout, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()