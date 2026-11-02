import json
import tempfile
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.data.feature_extractor import FEATURE_COLUMNS
from src.models.prediction_audit import run_prediction_audit


class TestPredictionAudit(unittest.TestCase):
    def test_audit_reproduces_metrics_and_explains_saved_scan_scores(self):
        with tempfile.TemporaryDirectory(prefix="prediction_audit_test_") as temporary_dir:
            report = run_prediction_audit(temporary_dir)
            output_dir = Path(temporary_dir)

            self.assertEqual(
                Path(report["model_file"]).as_posix(),
                "src/models/saved/LogisticRegression_combined.pkl",
            )
            self.assertEqual(report["feature_columns"], FEATURE_COLUMNS)
            self.assertEqual(report["positive_class"], 1)
            self.assertTrue(report["saved_evaluation_metrics_match"])
            self.assertFalse(report["held_out_test_metrics"]["calibration_fit_performed"])
            self.assertFalse(report["independent_external_repository_labels_available"])

            metrics = report["held_out_test_metrics"]
            self.assertEqual(metrics["sample_count"], 2572)
            self.assertEqual(metrics["defective_count"], 25)
            self.assertGreater(metrics["brier_score"], metrics["prevalence_only_baseline_brier_score"])
            self.assertGreater(metrics["log_loss"], metrics["prevalence_only_baseline_log_loss"])

            calibration_bins = pd.read_csv(output_dir / "prediction_audit_calibration_bins.csv")
            self.assertEqual(len(calibration_bins), 10)
            self.assertEqual(int(calibration_bins["sample_count"].sum()), metrics["sample_count"])

            distributions = pd.read_csv(
                output_dir / "prediction_audit_repository_feature_distribution.csv"
            )
            self.assertEqual(distributions["feature"].tolist(), FEATURE_COLUMNS)
            self.assertEqual(
                dict(zip(distributions["feature"], distributions["scanner_outside_training_range_count"])),
                report["scanner_diagnostics"]["feature_outside_training_raw_range_count"],
            )

            contributions = pd.read_csv(
                output_dir / "prediction_audit_top_file_contributions.csv"
            )
            self.assertEqual(
                contributions.loc[contributions["rank"] == 1, "feature"].tolist(),
                FEATURE_COLUMNS,
            )
            model = joblib.load("src/models/saved/LogisticRegression_combined.pkl")
            top_contributions = contributions[contributions["rank"] == 1][
                "log_odds_contribution"
            ].sum()
            np.testing.assert_allclose(
                top_contributions + model.intercept_[0],
                report["scanner_diagnostics"]["high_score_analysis"]["top_files"][0][
                    "decision_reconstruction"
                ],
                atol=1e-10,
                rtol=1e-10,
            )

            persisted_report = json.loads(
                (output_dir / "prediction_audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual(persisted_report, report)
            self.assertTrue((output_dir / "prediction_audit_reliability_diagram.png").is_file())

            repeated_dir = output_dir / "repeated"
            repeated_report = run_prediction_audit(repeated_dir)
            self.assertEqual(repeated_report, report)
            for artifact_name in (
                "prediction_audit.json",
                "prediction_audit_calibration_bins.csv",
                "prediction_audit_repository_feature_distribution.csv",
                "prediction_audit_repository_scores.csv",
                "prediction_audit_top_file_contributions.csv",
            ):
                self.assertEqual(
                    (repeated_dir / artifact_name).read_bytes(),
                    (output_dir / artifact_name).read_bytes(),
                )


if __name__ == "__main__":
    unittest.main()
