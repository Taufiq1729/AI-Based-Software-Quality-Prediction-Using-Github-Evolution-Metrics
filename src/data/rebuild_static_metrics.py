"""
Regenerates benchmark datasets using:
1. Real AST-based Java Static Analyzer (java_analyzer.py)
2. Real Rename-Aware Git Evolution Miner (git_miner.py)
3. Preserves original defect labels (isDefective) and record metadata
4. Drops and logs unmapped rows with explicit documented policy
"""

import os
import sys
import json
import logging
import argparse
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.analyzers.java_analyzer import analyze_java_file, analyze_java_source, build_repository_context
from src.data.git_miner import mine_repository_evolution, _normalize_path
from src.data.feature_extractor import STATIC_FEATURES, EVOLUTION_FEATURES, FEATURE_COLUMNS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _source_relative_path(dataset_path: str) -> Optional[str]:
    """Extracts relative repository path from dataset Path field."""
    if not isinstance(dataset_path, str) or not dataset_path.strip():
        return None
    normalized = dataset_path.replace("\\", "/")
    marker = "/src/"
    idx = normalized.find(marker)
    if idx >= 0:
        return normalized[idx + 1:]
    if normalized.startswith("src/"):
        return normalized
    return None


def regenerate_release_dataset(
    csv_path: Path,
    checkout_dir: Path,
    repo_git_dir: Path,
    output_dir: Path
) -> Tuple[Path, int, List[Dict[str, Any]]]:
    """
    Regenerates static and evolution metrics for a single release CSV.
    """
    commit = csv_path.stem.removeprefix("dataset-")
    logger.info(f"Checking out commit {commit} for {csv_path.name}...")

    subprocess.run(
        ["git", "-C", str(checkout_dir), "checkout", "--quiet", "--force", "--detach", commit],
        check=True,
        capture_output=True,
        text=True,
    )

    logger.info(f"Building whole-project context for commit {commit}...")
    context = build_repository_context(str(checkout_dir))
    context_report = {
        "release": commit,
        "parsed_java_files": context.get("parsed_java_files", 0),
        "total_java_files": context.get("total_java_files", 0),
        "parse_failures": context.get("parse_failures", []),
        "unresolved_reference_counts": dict(Counter(
            item["resolution"] for item in context.get("unresolved_references", [])
        )),
        "unresolved_references": context.get("unresolved_references", []),
        "duplicate_fqcns": context.get("duplicate_fqcns", {}),
    }
    with open(output_dir / f"identity_context_{commit}.json", "w", encoding="utf-8") as f:
        json.dump(context_report, f, indent=2)

    df_raw = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df_raw)} records from {csv_path.name}")

    # Determine target defective column
    target_col = "isDefective" if "isDefective" in df_raw.columns else ("Buggy" if "Buggy" in df_raw.columns else df_raw.columns[-1])

    # First pass: map and identify valid files
    unmapped_rows = []
    valid_records = []
    needed_relative_files = set()

    for idx, row in df_raw.iterrows():
        rel_p = _source_relative_path(str(row.get("Path", "")))
        if not rel_p:
            unmapped_rows.append({
                "release": commit,
                "row_index": idx,
                "ID": row.get("ID", f"R_{idx}"),
                "Name": str(row.get("Name", "")),
                "LongName": str(row.get("LongName", "")),
                "Path": str(row.get("Path", "")),
                "reason": "Missing or invalid source file relative path."
            })
            continue

        full_source_path = checkout_dir / rel_p
        if not full_source_path.is_file():
            unmapped_rows.append({
                "release": commit,
                "row_index": idx,
                "ID": row.get("ID", f"R_{idx}"),
                "Name": str(row.get("Name", "")),
                "LongName": str(row.get("LongName", "")),
                "Path": str(row.get("Path", "")),
                "reason": f"Source file '{rel_p}' does not exist in commit '{commit}'."
            })
            continue

        needed_relative_files.add(rel_p)
        valid_records.append((idx, row, rel_p, full_source_path))

    # Mine rename-aware evolution history for all needed files up to this exact commit
    logger.info(f"Mining Git evolution history for {len(needed_relative_files)} files up to {commit}...")
    mined_evolution = mine_repository_evolution(
        repo_path=str(repo_git_dir),
        to_commit=commit,
        target_files=list(needed_relative_files)
    )

    # Second pass: extract static metrics for each class and join with evolution
    logger.info(f"Extracting static metrics for {len(valid_records)} class records...")
    regenerated_rows = []
    file_content_cache: Dict[str, str] = {}

    for idx, row, rel_p, full_path in valid_records:
        name = str(row.get("Name", ""))
        long_name = str(row.get("LongName", ""))
        line = int(row.get("Line", 1)) if pd.notnull(row.get("Line")) else 1
        end_line = int(row.get("EndLine", line)) if pd.notnull(row.get("EndLine")) else line
        defect_val = int(row.get(target_col, 0)) if pd.notnull(row.get(target_col)) else 0

        # Cached file reading for maximum speed
        str_path = str(full_path)
        if str_path not in file_content_cache:
            with open(str_path, "r", encoding="utf-8", errors="replace") as f:
                file_content_cache[str_path] = f.read()

        content = file_content_cache[str_path]

        # Extract static metrics using authoritative Java analyzer
        static_feats = analyze_java_source(
            source_code=content,
            target_class_name=name,
            line_range=(line, end_line),
            relative_path=rel_p,
            project_context=context
        )

        # Get mined evolution metrics
        norm_p = _normalize_path(rel_p)
        evo_stats = mined_evolution.get(norm_p)
        if not evo_stats:
            for p, s in mined_evolution.items():
                if p.endswith(norm_p) or norm_p.endswith(p):
                    evo_stats = s
                    break
        if not evo_stats:
            evo_stats = {"code_churn": 0, "revision_count": 0, "developer_count": 0}

        row_dict = {
            "release": commit,
            "ID": row.get("ID", f"R_{idx}"),
            "Name": name,
            "LongName": long_name,
            "Path": rel_p,
            "Line": line,
            "EndLine": end_line,
        }

        # 12 static metrics
        for col in STATIC_FEATURES:
            row_dict[col] = float(static_feats.get(col, 0.0))

        # 3 evolution metrics
        for col in EVOLUTION_FEATURES:
            row_dict[col] = float(evo_stats.get(col, 0))

        # Target defect label
        row_dict["isDefective"] = defect_val
        regenerated_rows.append(row_dict)

    df_out = pd.DataFrame(regenerated_rows)
    out_file = output_dir / csv_path.name
    df_out.to_csv(out_file, index=False)
    logger.info(f"Wrote {len(df_out)} regenerated records to {out_file} (excluded {len(unmapped_rows)} unmapped)")

    return out_file, len(df_out), unmapped_rows


def regenerate_all_benchmarks(
    raw_dir: str = "data/raw/dataset/junit4",
    repo_dir: str = "data/repos/junit4.git",
    output_dir: str = "data/derived/junit4_regenerated",
    target_commits: Optional[List[str]] = None
) -> List[Path]:
    raw_path = Path(raw_dir)
    git_path = Path(repo_dir).resolve()
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(raw_path.glob("dataset-*.csv"))
    if target_commits:
        csv_files = [c for c in csv_files if any(commit in c.stem for commit in target_commits)]

    if not csv_files:
        raise FileNotFoundError(f"No CSVs found in {raw_path}")

    all_unmapped = []
    regenerated_files = []

    with tempfile.TemporaryDirectory(prefix="sqam-regen-") as temp_dir:
        checkout_dir = Path(temp_dir) / "junit4_checkout"
        logger.info(f"Cloning {git_path} into temporary checkout: {checkout_dir}...")
        subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", str(git_path), str(checkout_dir)],
            check=True,
            capture_output=True,
            text=True
        )

        for csv_file in csv_files:
            out_file, count, unmapped = regenerate_release_dataset(
                csv_path=csv_file,
                checkout_dir=checkout_dir,
                repo_git_dir=git_path,
                output_dir=out_path
            )
            regenerated_files.append(out_file)
            all_unmapped.extend(unmapped)

    if all_unmapped:
        unmapped_manifest = out_path / "unmapped_records.json"
        with open(unmapped_manifest, "w", encoding="utf-8") as f:
            json.dump(all_unmapped, f, indent=2)
        logger.info(f"Total unmapped records: {len(all_unmapped)}. Manifest: {unmapped_manifest}")

    return regenerated_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default="data/raw/dataset/junit4")
    parser.add_argument("--repo-dir", default="data/repos/junit4.git")
    parser.add_argument("--output-dir", default="data/derived/junit4_regenerated")
    parser.add_argument("--commits", nargs="*", default=None)
    args = parser.parse_args()

    regenerate_all_benchmarks(
        raw_dir=args.raw_dir,
        repo_dir=args.repo_dir,
        output_dir=args.output_dir,
        target_commits=args.commits
    )


if __name__ == "__main__":
    main()
