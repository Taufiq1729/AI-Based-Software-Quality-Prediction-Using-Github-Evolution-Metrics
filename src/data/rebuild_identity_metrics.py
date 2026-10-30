"""Recalculate package-qualified inheritance and inward-coupling features.

This staged Java-only rebuild preserves raw datasets and promotes regenerated
release CSVs only after record IDs, labels, and unrelated features validate.
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "dataset" / "junit4"
DERIVED_DIR = PROJECT_ROOT / "data" / "derived" / "junit4_regenerated"
REPO_GIT_DIR = PROJECT_ROOT / "data" / "repos" / "junit4.git"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit" / "identity_fix"

if str(PROJECT_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(PROJECT_ROOT))

from src.analyzers.java_analyzer import analyze_java_source, build_repository_context
from src.data.feature_extractor import STATIC_FEATURES
from src.data.rebuild_static_metrics import _source_relative_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rebuild_identity_metrics")

IDENTITY_FEATURES = ["DIT", "NOC", "CBOI"]
UNCHANGED_FEATURES = [feature for feature in STATIC_FEATURES if feature not in IDENTITY_FEATURES]


def _git(args: List[str]) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True, errors="replace")
    return result.stdout.strip()


def _json_write(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def _snapshot_before(release_files: List[Path], path: Path) -> pd.DataFrame:
    if path.exists():
        frame = pd.read_csv(path)
        logger.info("Reusing preserved before snapshot %s", path)
        return frame

    frames = []
    for release_file in release_files:
        data = pd.read_csv(release_file)
        columns = ["release", "ID", "Name", "Path", "isDefective"] + STATIC_FEATURES
        frames.append(data[columns].copy())
    before = pd.concat(frames, ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    before.to_csv(path, index=False)
    return before


def _write_context_findings(context: Dict[str, Any], commit: str, output_dir: Path) -> Dict[str, Any]:
    unresolved = context.get("unresolved_references", [])
    counts = dict(Counter(item.get("resolution", "unknown") for item in unresolved))
    path = output_dir / f"identity_context_{commit}.json"
    _json_write(path, {
        "commit": commit,
        "total_java_files": context.get("total_java_files", 0),
        "parsed_java_files": context.get("parsed_java_files", 0),
        "parse_failures": context.get("parse_failures", []),
        "duplicate_fqcns": context.get("duplicate_fqcns", {}),
        "unresolved_reference_counts": counts,
        "unresolved_references": unresolved,
    })
    return {"commit": commit, "diagnostic_file": path.name, **counts,
            "parse_failures": len(context.get("parse_failures", [])),
            "duplicate_fqcn_count": len(context.get("duplicate_fqcns", {}))}


def _rebuild_release(
    commit: str,
    checkout: Path,
    current_path: Path,
    stage_path: Path,
    stage_dir: Path,
) -> Dict[str, Any]:
    requested_commit = commit
    _git(["git", "-C", str(checkout), "checkout", "--quiet", "--force", "--detach", requested_commit])
    actual_commit = _git(["git", "-C", str(checkout), "rev-parse", "HEAD"])
    if actual_commit != requested_commit:
        raise RuntimeError(f"Requested {requested_commit}, checked out {actual_commit}")

    context = build_repository_context(str(checkout))
    current = pd.read_csv(current_path)
    if current["ID"].duplicated().any():
        raise ValueError(f"Duplicate IDs in current dataset {current_path}")

    source_cache: Dict[str, str] = {}
    changed_identity_values = Counter()
    row_changes = {feature: 0 for feature in IDENTITY_FEATURES}
    for row_index, row in current.iterrows():
        relative_path = str(row["Path"]).replace("\\", "/")
        source_path = checkout / relative_path
        if not source_path.is_file():
            raise FileNotFoundError(f"Retained row {row['ID']} source missing at {commit}: {relative_path}")
        if relative_path not in source_cache:
            source_cache[relative_path] = source_path.read_text(encoding="utf-8", errors="replace")
        line = int(row["Line"]) if pd.notnull(row["Line"]) else 1
        end_line = int(row["EndLine"]) if pd.notnull(row["EndLine"]) else line
        new_metrics = analyze_java_source(
            source_code=source_cache[relative_path],
            target_class_name=str(row["Name"]),
            line_range=(line, end_line),
            relative_path=relative_path,
            project_context=context,
        )
        for feature in IDENTITY_FEATURES:
            before_value = float(row[feature])
            after_value = float(new_metrics[feature])
            current.at[row_index, feature] = after_value
            if not np.isclose(before_value, after_value, rtol=0.0, atol=1e-12):
                row_changes[feature] += 1

    if current["ID"].duplicated().any():
        raise AssertionError(f"Identity recalculation changed ID uniqueness for {commit}")
    stage_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = stage_path.with_suffix(".csv.tmp")
    current.to_csv(temporary, index=False)
    temporary.replace(stage_path)

    diagnostics = _write_context_findings(context, commit, stage_dir)
    logger.info(
        "Release %s: %d rows; changed DIT/NOC/CBOI=%s; unresolved=%s; parse failures=%s",
        commit, len(current), row_changes, diagnostics, len(context.get("parse_failures", [])),
    )
    return {
        "commit": commit,
        "head_verified": actual_commit,
        "rows": len(current),
        "changed_rows": row_changes,
        "diagnostics": diagnostics,
    }


def rebuild_identity_metrics(
    raw_dir: Path = RAW_DIR,
    derived_dir: Path = DERIVED_DIR,
    repo_git_dir: Path = REPO_GIT_DIR,
    audit_dir: Path = AUDIT_DIR,
) -> Dict[str, Any]:
    raw_files = sorted(raw_dir.glob("dataset-*.csv"))
    current_files = sorted(derived_dir.glob("dataset-*.csv"))
    if len(raw_files) != 12 or len(current_files) != 12:
        raise ValueError(f"Expected 12 raw and 12 derived release CSVs; found {len(raw_files)} and {len(current_files)}")
    current_by_name = {path.name: path for path in current_files}
    if set(current_by_name) != {path.name for path in raw_files}:
        raise ValueError("Raw and derived release filename sets do not match")

    before_path = audit_dir / "before_static_metrics.csv"
    before = _snapshot_before(current_files, before_path)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    stage_dir = audit_dir / f"staged_{run_id}"
    if stage_dir.exists():
        raise FileExistsError(f"Staging directory already exists: {stage_dir}")
    staged_csv_dir = stage_dir / "releases"
    staged_csv_dir.mkdir(parents=True)

    release_results = []
    with __import__("tempfile").TemporaryDirectory(prefix="sqam-identity-") as temporary:
        checkout = Path(temporary) / "junit4"
        _git(["git", "clone", "--quiet", "--no-hardlinks", str(repo_git_dir), str(checkout)])
        for raw_path in raw_files:
            commit = raw_path.stem.removeprefix("dataset-")
            release_results.append(_rebuild_release(
                commit,
                checkout,
                current_by_name[raw_path.name],
                staged_csv_dir / raw_path.name,
                stage_dir,
            ))

    after_parts = []
    for path in sorted(staged_csv_dir.glob("dataset-*.csv")):
        frame = pd.read_csv(path)
        frame["release"] = path.stem.removeprefix("dataset-")
        after_parts.append(frame)
    after = pd.concat(after_parts, ignore_index=True)

    unmapped_records = []
    for raw_path in raw_files:
        commit = raw_path.stem.removeprefix("dataset-")
        raw = pd.read_csv(raw_path)
        retained_ids = set(after.loc[after["release"].eq(commit), "ID"])
        target_column = "isDefective" if "isDefective" in raw else "Buggy"
        for row_index, row in raw.iterrows():
            if row["ID"] in retained_ids:
                continue
            relative_path = _source_relative_path(str(row.get("Path", "")))
            reason = (
                f"Source file '{relative_path}' does not exist in commit '{commit}'."
                if relative_path else "Missing or invalid source file relative path."
            )
            unmapped_records.append({
                "release": commit,
                "row_index": int(row_index),
                "ID": row["ID"],
                "Name": str(row.get("Name", "")),
                "LongName": str(row.get("LongName", "")),
                "Path": str(row.get("Path", "")),
                "isDefective": int(row.get(target_column, 0)) if pd.notnull(row.get(target_column)) else 0,
                "reason": reason,
            })
    _json_write(stage_dir / "unmapped_records.json", unmapped_records)

    keys = ["release", "ID"]
    if before.duplicated(keys).any() or after.duplicated(keys).any():
        raise ValueError("Duplicate release/ID keys prevent a safe before/after comparison")
    merged = before.merge(after, on=keys, suffixes=("_before", "_after"), validate="one_to_one")
    if len(merged) != len(before) or len(merged) != len(after):
        raise ValueError("Regenerated records do not preserve the exact retained release/ID set")
    if not merged["isDefective_before"].equals(merged["isDefective_after"]):
        raise ValueError("Defect labels changed during identity feature recalculation")

    unrelated_changes = {}
    for feature in UNCHANGED_FEATURES:
        left = merged[f"{feature}_before"].to_numpy(dtype=float)
        right = merged[f"{feature}_after"].to_numpy(dtype=float)
        unrelated_changes[feature] = int((left != right).sum())
    if any(unrelated_changes.values()):
        raise ValueError(f"Unexpected changes to unrelated static features: {unrelated_changes}")

    comparison_rows = []
    summary_rows = []
    for feature in STATIC_FEATURES:
        left = merged[f"{feature}_before"].to_numpy(dtype=float)
        right = merged[f"{feature}_after"].to_numpy(dtype=float)
        delta = right - left
        changed = ~np.isclose(left, right, rtol=0.0, atol=1e-12)
        summary_rows.append({
            "feature": feature,
            "records": len(merged),
            "changed_records": int(changed.sum()),
            "mean_absolute_change": float(np.mean(np.abs(delta))),
            "maximum_absolute_change": float(np.max(np.abs(delta))),
            "unchanged_feature_verified": feature not in IDENTITY_FEATURES and not changed.any(),
        })
        if feature in IDENTITY_FEATURES:
            comparison_rows.append(pd.DataFrame({
                "release": merged["release"],
                "ID": merged["ID"],
                "Name": merged["Name_before"],
                "Path": merged["Path_before"],
                "isDefective": merged["isDefective_before"],
                "feature": feature,
                "before": left,
                "after": right,
                "delta": delta,
            }))

    comparisons = pd.concat(comparison_rows, ignore_index=True)
    comparisons.to_csv(audit_dir / "before_after_identity_features.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(audit_dir / "identity_feature_change_summary.csv", index=False)

    raw_label_checks = []
    for raw_path in raw_files:
        raw = pd.read_csv(raw_path)
        commit = raw_path.stem.removeprefix("dataset-")
        raw_target = "isDefective" if "isDefective" in raw else "Buggy"
        regenerated = after.loc[after["release"].eq(commit)].set_index("ID")
        source_labels = raw.set_index("ID")[raw_target].fillna(0).astype(int)
        retained_labels = regenerated["isDefective"].fillna(0).astype(int)
        labels = source_labels.reindex(retained_labels.index)
        if labels.isna().any() or not labels.astype(int).equals(retained_labels):
            raise ValueError(f"Original labels do not match regenerated release {commit}")
        raw_label_checks.append({"release": commit, "raw_records": len(raw),
                                 "retained_records": len(regenerated), "label_mismatches": 0,
                                 "excluded_raw_records": len(raw) - len(regenerated)})

    manifest = {
        "run_id": run_id,
        "identity_features_recalculated": IDENTITY_FEATURES,
        "unrelated_features_unchanged": unrelated_changes,
        "record_count": len(after),
        "release_count": len(release_results),
        "label_checks": raw_label_checks,
        "releases": release_results,
        "staging_dir": str(stage_dir),
    }
    _json_write(audit_dir / "identity_rebuild_manifest.json", manifest)

    for staged_path in sorted(staged_csv_dir.glob("dataset-*.csv")):
        os.replace(staged_path, derived_dir / staged_path.name)
    staged_unmapped = stage_dir / "unmapped_records.json"
    os.replace(staged_unmapped, derived_dir / "unmapped_records.json")
    for diagnostic_path in stage_dir.glob("identity_context_*.json"):
        os.replace(diagnostic_path, derived_dir / diagnostic_path.name)

    _json_write(audit_dir / "identity_rebuild_manifest.json", {**manifest, "promoted": True})
    logger.info("Promoted qualified-identity features for %d rows across %d releases", len(after), len(release_results))
    return {**manifest, "promoted": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--derived-dir", type=Path, default=DERIVED_DIR)
    parser.add_argument("--repo-git-dir", type=Path, default=REPO_GIT_DIR)
    parser.add_argument("--audit-dir", type=Path, default=AUDIT_DIR)
    args = parser.parse_args()
    result = rebuild_identity_metrics(args.raw_dir, args.derived_dir, args.repo_git_dir, args.audit_dir)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
