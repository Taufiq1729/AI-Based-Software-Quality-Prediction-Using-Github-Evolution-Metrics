"""Research validation audit for the Java defect-prediction pipeline.

Run from the repository root with ``python src/data/final_validation_audit.py``.
Static checks are resumable per release and preserve record-level evidence.
"""

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    accuracy_score,
    auc,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT_DIR = PROJECT_ROOT / "data" / "audit"
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "dataset" / "junit4"
DERIVED_DIR = PROJECT_ROOT / "data" / "derived" / "junit4_regenerated"
REPO_GIT_DIR = PROJECT_ROOT / "data" / "repos" / "junit4.git"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "src" / "models" / "saved"
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
TOLERANCE = 1e-9
AUDIT_VERSION = 4

if str(PROJECT_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(PROJECT_ROOT))

from src.analyzers.java_analyzer import analyze_java_source, build_repository_context
from src.data.feature_extractor import FEATURE_COLUMNS, STATIC_FEATURES
from src.data.preprocessing import TEST_RELEASE_COMMITS, TRAIN_RELEASE_COMMITS
from src.data.rebuild_static_metrics import _source_relative_path
from src.data.git_miner import mine_file_history, mine_repository_evolution

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("final_validation_audit")


def _run_git(args: List[str], cwd: Optional[Path] = None) -> str:
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
        errors="replace",
    )
    return result.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def _atomic_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def _commit_date(commit: str) -> datetime:
    value = _run_git(["git", f"--git-dir={REPO_GIT_DIR}", "show", "-s", "--format=%cI", commit])
    return datetime.fromisoformat(value)


def _commit_tags(commit: str) -> List[str]:
    value = _run_git(["git", f"--git-dir={REPO_GIT_DIR}", "tag", "--points-at", commit])
    return [tag for tag in value.splitlines() if tag]


def _is_cached_release_valid(commit: str, raw_path: Path, derived_path: Path, release_dir: Path) -> bool:
    result_path = release_dir / "static_records.csv"
    marker_path = release_dir / "complete.json"
    if not result_path.is_file() or not marker_path.is_file():
        return False
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        cached = pd.read_csv(result_path)
        required_columns = {"qualified_class_identity", "qualified_identity_resolution"}
        raw_count = len(pd.read_csv(raw_path))
        derived_count = len(pd.read_csv(derived_path))
        return (
            marker.get("audit_version") == AUDIT_VERSION
            and marker.get("commit") == commit
            and marker.get("raw_sha256") == _sha256(raw_path)
            and marker.get("derived_sha256") == _sha256(derived_path)
            and marker.get("raw_rows") == raw_count
            and marker.get("derived_rows") == derived_count
            and len(cached) == derived_count
            and required_columns.issubset(cached.columns)
        )
    except Exception:
        return False


def _inspect_mapping(source: str, class_name: str, line: int) -> Dict[str, Any]:
    import javalang

    tree = javalang.parse.parse(source)
    class_types = (javalang.tree.ClassDeclaration, javalang.tree.InterfaceDeclaration)
    nodes = [node for _, node in tree.filter(class_types)]
    named = [node for node in nodes if getattr(node, "name", None) == class_name]
    near_line = [
        node for node in nodes
        if getattr(getattr(node, "position", None), "line", None) is not None
        and abs(node.position.line - line) <= 2
    ]
    selected = near_line[0] if near_line else (named[0] if named else None)
    if near_line:
        method = "line"
    elif named:
        method = "name"
    else:
        method = "fallback"

    conflict = bool(selected is not None and selected.name != class_name)
    return {
        "mapping_method": method,
        "same_name_candidates_in_file": len(named),
        "near_line_candidates": len(near_line),
        "selected_class": getattr(selected, "name", "") if selected is not None else "",
        "selected_line": getattr(getattr(selected, "position", None), "line", None),
        "line_name_conflict": conflict,
    }


def _build_release_static_audit(
    commit: str,
    raw_path: Path,
    derived_path: Path,
    checkout_dir: Path,
    release_dir: Path,
) -> pd.DataFrame:
    logger.info("Auditing static features for release %s", commit)
    _run_git(["git", "-C", str(checkout_dir), "checkout", "--quiet", "--force", "--detach", commit])
    actual_head = _run_git(["git", "-C", str(checkout_dir), "rev-parse", "HEAD"])
    if actual_head != commit:
        raise RuntimeError(f"Checkout mismatch: requested {commit}, got {actual_head}")

    context = build_repository_context(str(checkout_dir))
    raw = pd.read_csv(raw_path)
    regenerated = pd.read_csv(derived_path)
    raw_by_id = raw.set_index("ID", drop=False)
    derived_by_id = regenerated.set_index("ID", drop=False)
    records: List[Dict[str, Any]] = []
    source_cache: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
    parser_cache: Dict[str, Tuple[str, str, List[str]]] = {}

    for row_number, (_, generated_row) in enumerate(regenerated.iterrows()):
        record_id = generated_row["ID"]
        raw_row = raw_by_id.loc[record_id]
        relative_path = str(generated_row["Path"])
        source_path = checkout_dir / relative_path
        key = relative_path.replace("\\", "/")
        result: Dict[str, Any] = {
            "release": commit,
            "ID": record_id,
            "Name": str(generated_row["Name"]),
            "Path": key,
            "row_number": row_number,
            "status": "compared",
            "parser_mode": "unknown",
            "parse_error": "",
            "mapping_method": "not_checked",
            "same_name_candidates_in_file": 0,
            "near_line_candidates": 0,
            "selected_class": "",
            "selected_line": None,
            "line_name_conflict": False,
            "global_same_name_class_count": 0,
            "label_matches_raw": int(generated_row["isDefective"]) == int(raw_row.get("isDefective", raw_row.get("Buggy", 0))),
            "raw_label": int(raw_row.get("isDefective", raw_row.get("Buggy", 0))),
            "regenerated_label": int(generated_row["isDefective"]),
            "analysis_error": "",
        }

        if not source_path.is_file():
            result["status"] = "missing_source"
            result["analysis_error"] = f"Source absent at checked-out commit: {relative_path}"
            for feature in STATIC_FEATURES:
                result[f"generated_{feature}"] = float(generated_row[feature])
                result[f"recomputed_{feature}"] = np.nan
                result[f"abs_error_{feature}"] = np.nan
                result[f"exact_{feature}"] = False
            records.append(result)
            continue

        if key not in source_cache:
            try:
                source_cache[key] = (source_path.read_text(encoding="utf-8", errors="replace"), None)
            except Exception as error:
                source_cache[key] = (None, f"{type(error).__name__}: {error}")
        source, source_error = source_cache[key]
        if source is None:
            result["status"] = "source_read_error"
            result["analysis_error"] = source_error or "Unable to read source"
            records.append(result)
            continue

        if key not in parser_cache:
            try:
                mapping = _inspect_mapping(source, str(generated_row["Name"]), int(generated_row["Line"]))
                parser_cache[key] = ("ast", "", [])
            except Exception as error:
                mapping = {
                    "mapping_method": "regex_fallback",
                    "same_name_candidates_in_file": 0,
                    "near_line_candidates": 0,
                    "selected_class": "",
                    "selected_line": None,
                    "line_name_conflict": False,
                }
                parser_cache[key] = ("regex_fallback", f"{type(error).__name__}: {error}", [])
        else:
            mode, parse_error, _ = parser_cache[key]
            if mode == "ast":
                mapping = _inspect_mapping(source, str(generated_row["Name"]), int(generated_row["Line"]))
            else:
                mapping = {
                    "mapping_method": "regex_fallback",
                    "same_name_candidates_in_file": 0,
                    "near_line_candidates": 0,
                    "selected_class": "",
                    "selected_line": None,
                    "line_name_conflict": False,
                }

        mode, parse_error, _ = parser_cache[key]
        result["parser_mode"] = mode
        result["parse_error"] = parse_error
        result.update(mapping)
        result["global_same_name_class_count"] = sum(
            definition["name"] == str(generated_row["Name"])
            for definitions in context.get("class_definitions", {}).values()
            for definition in definitions
        )
        normalized_target = str(generated_row["Name"]).replace("$", ".")
        file_definitions = context.get("class_definitions", {}).get(key, [])
        target_names = [normalized_target]
        long_name = str(generated_row.get("LongName", ""))
        if long_name:
            target_names.append(long_name.split("<", 1)[0].replace("$", "."))
        qualified_matches = [
            definition for definition in file_definitions
            if any(
                definition["identity"] == target
                or definition["identity"].endswith("." + target)
                for target in target_names if target
            )
        ]
        if not qualified_matches:
            qualified_matches = [
                definition for definition in file_definitions
                if definition["name"] == str(generated_row["Name"])
            ]
        result["qualified_class_identity"] = (
            qualified_matches[0]["identity"] if len(qualified_matches) == 1 else ""
        )
        result["qualified_identity_resolution"] = (
            "resolved" if len(qualified_matches) == 1
            else "ambiguous" if len(qualified_matches) > 1
            else "anonymous_or_synthetic" if re.search(r"\$\d+", str(generated_row["Name"]))
            else "unresolved"
        )

        try:
            line = int(generated_row["Line"]) if pd.notnull(generated_row["Line"]) else 1
            end_line = int(generated_row["EndLine"]) if pd.notnull(generated_row["EndLine"]) else line
            recomputed = analyze_java_source(
                source_code=source,
                target_class_name=str(generated_row["Name"]),
                line_range=(line, end_line),
                relative_path=relative_path,
                project_context=context,
            )
        except Exception as error:
            result["status"] = "analysis_error"
            result["analysis_error"] = f"{type(error).__name__}: {error}"
            recomputed = {}

        if mode == "regex_fallback" and result["status"] == "compared":
            result["status"] = "regex_fallback_compared"
        if result["line_name_conflict"] and result["status"] in ("compared", "regex_fallback_compared"):
            result["status"] = "line_name_conflict"
        if result["same_name_candidates_in_file"] > 1 and result["status"] in ("compared", "regex_fallback_compared"):
            result["status"] = "duplicate_name_in_file"
        if result["near_line_candidates"] > 1 and result["status"] in ("compared", "regex_fallback_compared"):
            result["status"] = "ambiguous_line_candidates"

        for feature in STATIC_FEATURES:
            generated_value = float(generated_row[feature])
            recomputed_value = float(recomputed[feature]) if feature in recomputed else np.nan
            error = abs(generated_value - recomputed_value) if np.isfinite(recomputed_value) else np.nan
            result[f"generated_{feature}"] = generated_value
            result[f"recomputed_{feature}"] = recomputed_value
            result[f"abs_error_{feature}"] = error
            result[f"exact_{feature}"] = bool(error == 0.0) if np.isfinite(error) else False
        records.append(result)

    frame = pd.DataFrame(records)
    _atomic_csv(frame, release_dir / "static_records.csv")
    marker = {
        "audit_version": AUDIT_VERSION,
        "commit": commit,
        "head_verified": actual_head,
        "raw_sha256": _sha256(raw_path),
        "derived_sha256": _sha256(derived_path),
        "raw_rows": len(raw),
        "derived_rows": len(regenerated),
        "audited_rows": len(frame),
        "completed_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    _atomic_json(marker, release_dir / "complete.json")
    return frame


def run_static_audit(audit_dir: Path, selected_commits: Optional[List[str]], force: bool) -> Dict[str, Any]:
    output_dir = audit_dir / "static"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_files = sorted(RAW_DIR.glob("dataset-*.csv"))
    commits = [path.stem.removeprefix("dataset-") for path in raw_files]
    if selected_commits:
        unknown = set(selected_commits) - set(commits)
        if unknown:
            raise ValueError(f"Unknown release commits requested: {sorted(unknown)}")
        commits = [commit for commit in commits if commit in selected_commits]

    all_frames = []
    with tempfile.TemporaryDirectory(prefix="sqam-static-audit-") as temp:
        checkout = Path(temp) / "junit4"
        _run_git(["git", "clone", "--quiet", "--no-hardlinks", str(REPO_GIT_DIR), str(checkout)])
        for commit in commits:
            raw_path = RAW_DIR / f"dataset-{commit}.csv"
            derived_path = DERIVED_DIR / raw_path.name
            if not derived_path.is_file():
                raise FileNotFoundError(f"Missing regenerated release file: {derived_path}")
            release_dir = output_dir / commit
            if not force and _is_cached_release_valid(commit, raw_path, derived_path, release_dir):
                logger.info("Resuming from completed static audit for %s", commit)
                frame = pd.read_csv(release_dir / "static_records.csv")
            else:
                frame = _build_release_static_audit(commit, raw_path, derived_path, checkout, release_dir)
            all_frames.append(frame)

    combined = pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()
    if combined.empty:
        raise ValueError("Static audit produced no records")
    _write_static_summaries(combined, output_dir)
    return {
        "releases_audited": commits,
        "records_audited": len(combined),
        "records_missing_or_failed": int((~combined["status"].isin(["compared", "regex_fallback_compared", "line_name_conflict", "duplicate_name_in_file"])).sum()),
        "summary_csv": str(output_dir / "static_feature_summary.csv"),
    }


def _write_static_summaries(records: pd.DataFrame, output_dir: Path) -> None:
    summary_rows = []
    all_error_rows = []
    for feature in STATIC_FEATURES:
        error_column = f"abs_error_{feature}"
        errors = pd.to_numeric(records[error_column], errors="coerce")
        valid = errors.notna()
        exact = records[f"exact_{feature}"].fillna(False).astype(bool)
        mismatch = (~valid) | (errors > TOLERANCE)
        summary_rows.append({
            "feature": feature,
            "retained_records": len(records),
            "compared_records": int(valid.sum()),
            "failed_or_uncompared_records": int((~valid).sum()),
            "exact_matches": int(exact.sum()),
            "exact_match_rate_all_retained": float(exact.sum() / len(records)),
            "within_tolerance_matches": int((valid & errors.le(TOLERANCE)).sum()),
            "within_tolerance_rate_all_retained": float((valid & errors.le(TOLERANCE)).sum() / len(records)),
            "mae_successful_comparisons": float(errors[valid].mean()) if valid.any() else np.nan,
            "max_absolute_error_successful_comparisons": float(errors[valid].max()) if valid.any() else np.nan,
            "mismatched_records_over_tolerance_or_failed": int(mismatch.sum()),
            "tolerance": TOLERANCE,
        })
        for _, row in records.loc[mismatch].iterrows():
            all_error_rows.append({
                "release": row["release"],
                "ID": row["ID"],
                "Name": row["Name"],
                "Path": row["Path"],
                "status": row["status"],
                "feature": feature,
                "generated": row.get(f"generated_{feature}"),
                "recomputed": row.get(f"recomputed_{feature}"),
                "absolute_error": row.get(error_column),
                "analysis_error": row.get("analysis_error", ""),
                "parse_error": row.get("parse_error", ""),
            })

    _atomic_csv(pd.DataFrame(summary_rows), output_dir / "static_feature_summary.csv")
    _atomic_csv(pd.DataFrame(all_error_rows), output_dir / "static_mismatches.csv")
    _atomic_csv(records, output_dir / "static_records_all_releases.csv")

    failure_columns = [
        "release", "ID", "Name", "Path", "status", "parser_mode", "parse_error",
        "mapping_method", "same_name_candidates_in_file", "near_line_candidates",
        "selected_class", "selected_line", "line_name_conflict", "global_same_name_class_count",
        "qualified_class_identity", "qualified_identity_resolution", "analysis_error",
    ]
    failures = records.loc[
        records["status"].isin(["missing_source", "source_read_error", "analysis_error"])
        | records["parser_mode"].eq("regex_fallback")
        | records["line_name_conflict"]
        | records["same_name_candidates_in_file"].gt(1)
        | records["near_line_candidates"].gt(1)
        | records["global_same_name_class_count"].gt(1)
        | records["qualified_identity_resolution"].ne("resolved")
    ]
    _atomic_csv(failures[failure_columns], output_dir / "static_mapping_parser_findings.csv")

    collisions = records.loc[
        records["global_same_name_class_count"].fillna(0).gt(1),
        ["release", "ID", "Name", "Path", "global_same_name_class_count"],
    ].drop_duplicates(["release", "ID"])
    _atomic_csv(collisions, output_dir / "duplicate_simple_name_records.csv")
    collision_groups = collisions.groupby(["release", "Name"], as_index=False).agg(
        record_count=("ID", "nunique"),
        benchmark_paths=("Path", "nunique"),
        max_repository_definitions=("global_same_name_class_count", "max"),
    )
    _atomic_csv(collision_groups, output_dir / "duplicate_simple_name_groups.csv")

    release_rows = []
    for commit, group in records.groupby("release", sort=False):
        raw_path = RAW_DIR / f"dataset-{commit}.csv"
        derived_path = DERIVED_DIR / raw_path.name
        release_rows.append({
            "release": commit,
            "rows_audited": len(group),
            "rows_compared": int(group[[f"recomputed_{f}" for f in STATIC_FEATURES]].notna().all(axis=1).sum()),
            "rows_with_non_exact_feature": int((~group[[f"exact_{f}" for f in STATIC_FEATURES]].all(axis=1)).sum()),
            "regex_fallback_rows": int(group["parser_mode"].eq("regex_fallback").sum()),
            "line_name_conflict_rows": int(group["line_name_conflict"].fillna(False).sum()),
            "duplicate_name_in_file_rows": int(group["same_name_candidates_in_file"].fillna(0).gt(1).sum()),
            "ambiguous_line_candidate_rows": int(group["near_line_candidates"].fillna(0).gt(1).sum()),
            "global_duplicate_simple_name_rows": int(group["global_same_name_class_count"].fillna(0).gt(1).sum()),
            "missing_source_rows": int(group["status"].eq("missing_source").sum()),
            "raw_sha256": _sha256(raw_path),
            "derived_sha256": _sha256(derived_path),
        })
    _atomic_csv(pd.DataFrame(release_rows), output_dir / "static_release_summary.csv")


def _native_git_reference(repo: Path, file_path: str, commit: Optional[str] = None) -> Dict[str, int]:
    if repo.name.endswith(".git") and (repo.is_dir() or repo.is_file()):
        args = ["git", f"--git-dir={repo}", "log", "--follow", "-M", "--numstat",
                "--format=COMMIT:%H|%aE|%aN"]
    else:
        args = ["git", "-C", str(repo), "log", "--follow", "-M", "--numstat",
                "--format=COMMIT:%H|%aE|%aN"]
    args.append(commit or "HEAD")
    args.extend(["--", file_path])
    output = _run_git(args)
    revision_count = 0
    churn = 0
    authors = set()
    for line in output.splitlines():
        if line.startswith("COMMIT:"):
            parts = line[len("COMMIT:"):].split("|")
            authors.add((parts[1] or parts[2]).strip() if len(parts) > 2 else "unknown")
            revision_count += 1
        elif "\t" in line:
            fields = line.split("\t")
            if len(fields) >= 2:
                try:
                    churn += int(fields[0]) + int(fields[1])
                except ValueError:
                    continue
    return {"code_churn": churn, "revision_count": revision_count, "developer_count": len(authors)}


def run_git_fixture_audit(audit_dir: Path) -> Dict[str, Any]:
    output_dir = audit_dir / "git_evolution"
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory(prefix="sqam-git-audit-") as temp:
        repo = Path(temp) / "fixture"
        repo.mkdir()
        _run_git(["git", "init", "--quiet", str(repo)])
        _run_git(["git", "-C", str(repo), "config", "user.name", "Initial"])
        _run_git(["git", "-C", str(repo), "config", "user.email", "initial@example.test"])

        def commit(message: str, author: str, email: str, day: int) -> str:
            _run_git(["git", "-C", str(repo), "add", "-A"])
            env = os.environ.copy()
            date = f"2020-01-{day:02d}T12:00:00+00:00"
            env.update({"GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": email,
                        "GIT_COMMITTER_NAME": author, "GIT_COMMITTER_EMAIL": email,
                        "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})
            subprocess.run(["git", "-C", str(repo), "commit", "--quiet", "-m", message],
                           check=True, capture_output=True, text=True, env=env)
            return _run_git(["git", "-C", str(repo), "rev-parse", "HEAD"])

        ordinary = repo / "src" / "Ordinary.java"
        ordinary.parent.mkdir(parents=True)
        ordinary.write_text("class Ordinary {\n int a;\n}\n", encoding="utf-8")
        commit("ordinary add", "Dev One", "one@example.test", 1)
        ordinary.write_text("class Ordinary {\n int a;\n int b;\n}\n", encoding="utf-8")
        ordinary_cutoff = commit("ordinary edit", "Dev Two", "two@example.test", 2)
        ordinary.write_text("class Ordinary {\n int a;\n int b;\n int c;\n}\n", encoding="utf-8")
        ordinary_future = commit("ordinary future edit", "Dev Three", "three@example.test", 6)

        old_file = repo / "src" / "old" / "Moved.java"
        old_file.parent.mkdir(parents=True)
        old_file.write_text("class Moved {\n int a;\n}\n", encoding="utf-8")
        commit("moved add", "Dev One", "one@example.test", 3)
        old_file.write_text("class Moved {\n int a;\n int b;\n}\n", encoding="utf-8")
        commit("moved edit", "Dev Two", "two@example.test", 4)
        new_file = repo / "src" / "new" / "Moved.java"
        new_file.parent.mkdir(parents=True)
        _run_git(["git", "-C", str(repo), "mv", str(old_file.relative_to(repo)), str(new_file.relative_to(repo))])
        new_file.write_text("class Moved {\n int a;\n int b;\n int c;\n}\n", encoding="utf-8")
        rename_cutoff = commit("move and rename", "Dev Three", "three@example.test", 5)
        new_file.write_text("class Moved {\n int a;\n int b;\n int c;\n int d;\n}\n", encoding="utf-8")
        move_future = commit("post-release moved edit", "Dev Four", "four@example.test", 7)

        deleted_file = repo / "src" / "deleted" / "Deleted.java"
        deleted_file.parent.mkdir(parents=True)
        deleted_file.write_text("class Deleted {\n int first;\n}\n", encoding="utf-8")
        commit("deleted file add", "Dev One", "one@example.test", 8)
        deleted_file.write_text("class Deleted {\n int first;\n int second;\n}\n", encoding="utf-8")
        commit("deleted file edit", "Dev Two", "two@example.test", 9)
        _run_git(["git", "-C", str(repo), "rm", str(deleted_file.relative_to(repo))])
        deleted_commit = commit("delete file", "Dev Three", "three@example.test", 10)

        long_history = repo / "src" / "history" / "LongHistory.java"
        long_history.parent.mkdir(parents=True)
        long_history.write_text("class LongHistory {\n int revision0;\n}\n", encoding="utf-8")
        commit("long history initial", "Dev One", "one@example.test", 11)
        for day in range(12, 24):
            long_history.write_text(
                "class LongHistory {\n" + "".join(f" int revision{index};\n" for index in range(day - 10)) + "}\n",
                encoding="utf-8",
            )
            commit(f"long history edit {day}", f"Dev {day % 4}", f"dev{day % 4}@example.test", day)
        long_history_commit = _run_git(["git", "-C", str(repo), "rev-parse", "HEAD"])

        scenarios = [
            ("ordinary_at_cutoff", "src/Ordinary.java", ordinary_cutoff, "ordinary"),
            ("ordinary_after_future", "src/Ordinary.java", ordinary_future, "ordinary"),
            ("renamed_file_at_release", "src/new/Moved.java", rename_cutoff, "renamed"),
            ("moved_file_after_future", "src/new/Moved.java", move_future, "moved"),
            ("renamed_file_cutoff_no_lookahead", "src/new/Moved.java", rename_cutoff, "renamed"),
            ("deleted_file_history_at_delete_commit", "src/deleted/Deleted.java", deleted_commit, "deleted"),
            ("long_file_history", "src/history/LongHistory.java", long_history_commit, "long_history"),
        ]
        for scenario, path, target_commit, kind in scenarios:
            native = _native_git_reference(repo, path, target_commit)
            production = mine_file_history(str(repo), path, to_commit=target_commit)
            row = {"scenario": scenario, "path": path, "target_commit": target_commit,
                   "native_reference": native, "pipeline": production}
            for metric in ("code_churn", "revision_count", "developer_count"):
                row[f"native_{metric}"] = native[metric]
                row[f"pipeline_{metric}"] = production[metric]
                row[f"matches_{metric}"] = native[metric] == production[metric]
            rows.append(row)

        prior = _native_git_reference(repo, "src/new/Moved.java", rename_cutoff)
        after = _native_git_reference(repo, "src/new/Moved.java", move_future)
        rows.append({
            "scenario": "post_release_commit_exclusion",
            "path": "src/new/Moved.java",
            "target_commit": rename_cutoff,
            "native_reference": prior,
            "pipeline": mine_file_history(str(repo), "src/new/Moved.java", to_commit=rename_cutoff),
            "future_reference": after,
            "no_lookahead_verified": all(prior[key] != after[key] for key in prior),
        })

        repository_result = mine_repository_evolution(
            str(repo), to_commit=rename_cutoff, target_files=["src/new/Moved.java"]
        ).get("src/new/moved.java", {})
        expected = _native_git_reference(repo, "src/new/Moved.java", rename_cutoff)
        rows.append({
            "scenario": "repository_miner_matches_file_miner",
            "path": "src/new/Moved.java",
            "target_commit": rename_cutoff,
            "native_reference": expected,
            "pipeline": repository_result,
            "matches_all_metrics": repository_result == expected,
        })

    benchmark_samples = []
    for raw_path in sorted(RAW_DIR.glob("dataset-*.csv")):
        commit = raw_path.stem.removeprefix("dataset-")
        generated = pd.read_csv(DERIVED_DIR / raw_path.name)
        sample = generated.drop_duplicates("Path").iloc[0]
        path = str(sample["Path"]).replace("\\", "/")
        native = _native_git_reference(REPO_GIT_DIR, path, commit)
        generated_metrics = {key: int(sample[key]) for key in ("code_churn", "revision_count", "developer_count")}
        benchmark_row = {
            "scenario": f"benchmark_release_sample_{commit}",
            "path": path,
            "target_commit": commit,
            "native_reference": native,
            "pipeline": generated_metrics,
        }
        for metric in ("code_churn", "revision_count", "developer_count"):
            benchmark_row[f"native_{metric}"] = native[metric]
            benchmark_row[f"pipeline_{metric}"] = generated_metrics[metric]
            benchmark_row[f"matches_{metric}"] = native[metric] == generated_metrics[metric]
        benchmark_samples.append(benchmark_row)

    frame = pd.DataFrame(rows + benchmark_samples)
    _atomic_csv(frame, output_dir / "git_evolution_fixture_audit.csv")
    comparison_scenarios = {
        "ordinary_at_cutoff", "ordinary_after_future", "renamed_file_at_release",
        "moved_file_after_future", "renamed_file_cutoff_no_lookahead",
        "deleted_file_history_at_delete_commit", "long_file_history",
    }
    comparison_rows = frame[frame["scenario"].isin(comparison_scenarios)]
    metric_match_columns = [
        "matches_code_churn", "matches_revision_count", "matches_developer_count",
    ]
    all_metric_comparisons_match = bool(
        comparison_rows[metric_match_columns].astype("boolean").fillna(False).to_numpy(dtype=bool).all()
    )
    return {
        "scenarios": len(frame),
        "ordinary_rename_move_and_multi_developer_tests_match": all_metric_comparisons_match,
        "historical_release_sample_count": len(benchmark_samples),
        "all_historical_release_samples_match": bool(
            pd.DataFrame(benchmark_samples)[metric_match_columns].astype("boolean").fillna(False).to_numpy(dtype=bool).all()
        ),
        "output": str(output_dir / "git_evolution_fixture_audit.csv"),
    }


def run_parser_construct_probes(audit_dir: Path) -> Dict[str, Any]:
    import javalang

    quote = '"' * 3
    probes = {
        "java_module_declaration": "module sample { requires java.base; }",
        "local_var_inference": "class Sample { void f() { var value = 1; } }",
        "record_declaration": "record Point(int x, int y) {}",
        "text_block": "class Sample { String text = " + quote + "text" + quote + "; }",
        "sealed_class": "sealed class Base permits Child {} final class Child extends Base {}",
        "pattern_matching_instanceof": "class Sample { boolean f(Object x) { return x instanceof String value; } }",
        "switch_expression": "class Sample { int f(int x) { return switch (x) { case 1 -> 2; default -> 3; }; } }",
    }
    results = []
    for construct, source in probes.items():
        try:
            javalang.parse.parse(source)
            supported = True
            error = ""
        except Exception as exception:
            supported = False
            error = f"{type(exception).__name__}: {exception}"
        results.append({"construct": construct, "supported_by_installed_javalang": supported,
                        "error": error, "probe_source": source})
    output = {"javalang_version": getattr(javalang, "__version__", "unknown"),
              "probes": results,
              "note": "These probes identify grammar boundaries; the release audit separately records parser outcomes for all retained source files."}
    _atomic_json(output, audit_dir / "parser_construct_probes.json")
    return output


def run_dataset_audit(audit_dir: Path) -> Dict[str, Any]:
    output_dir = audit_dir / "dataset"
    output_dir.mkdir(parents=True, exist_ok=True)
    commits = [path.stem.removeprefix("dataset-") for path in sorted(RAW_DIR.glob("dataset-*.csv"))]
    missing = (set(TRAIN_RELEASE_COMMITS) | set(TEST_RELEASE_COMMITS)) - set(commits)
    if missing:
        raise ValueError(f"Configured train/test commits absent from raw releases: {sorted(missing)}")

    records = []
    for commit in commits:
        raw = pd.read_csv(RAW_DIR / f"dataset-{commit}.csv")
        derived = pd.read_csv(DERIVED_DIR / f"dataset-{commit}.csv")
        date = _commit_date(commit)
        tag_names = _commit_tags(commit)
        label_column = "isDefective" if "isDefective" in raw else "Buggy"
        raw_labels = raw.set_index("ID")[label_column].fillna(0).astype(int)
        derived_labels = derived.set_index("ID")["isDefective"].fillna(0).astype(int)
        matching = raw_labels.reindex(derived_labels.index)
        label_matches = matching.notna() & matching.eq(derived_labels)
        excluded_ids = raw.loc[~raw["ID"].isin(derived["ID"]), "ID"].tolist()
        counts = derived_labels.value_counts().to_dict()
        records.append({
            "release_name": ",".join(tag_names) if tag_names else "unlabeled_commit",
            "commit": commit,
            "commit_date": date.isoformat(),
            "partition": "train" if commit in TRAIN_RELEASE_COMMITS else "test" if commit in TEST_RELEASE_COMMITS else "unused",
            "raw_samples": len(raw),
            "total_samples": len(derived),
            "defective_samples": int(counts.get(1, 0)),
            "non_defective_samples": int(counts.get(0, 0)),
            "defect_percentage": float(counts.get(1, 0) * 100 / len(derived)) if len(derived) else 0.0,
            "labels_matching_original_id": int(label_matches.sum()),
            "retained_label_mismatches": int((~label_matches).sum()),
            "excluded_record_ids": json.dumps(excluded_ids),
            "git_tags": json.dumps(tag_names),
        })

    frame = pd.DataFrame(records)
    frame["_date"] = pd.to_datetime(frame["commit_date"], utc=True)
    frame = frame.sort_values("_date").drop(columns="_date").reset_index(drop=True)
    ordered = pd.to_datetime(frame["commit_date"], utc=True).is_monotonic_increasing
    train_dates = pd.to_datetime(frame.loc[frame["partition"].eq("train"), "commit_date"], utc=True)
    test_dates = pd.to_datetime(frame.loc[frame["partition"].eq("test"), "commit_date"], utc=True)
    split_disjoint = set(TRAIN_RELEASE_COMMITS).isdisjoint(TEST_RELEASE_COMMITS)
    strict_temporal = bool(train_dates.max() < test_dates.min())
    _atomic_csv(frame, output_dir / "release_distribution.csv")

    unmapped = json.loads((DERIVED_DIR / "unmapped_records.json").read_text(encoding="utf-8"))
    train_rows = frame[frame["partition"].eq("train")]
    test_rows = frame[frame["partition"].eq("test")]
    audit = {
        "release_count": len(frame),
        "release_dates_sorted": bool(ordered),
        "train_test_commit_sets_disjoint": bool(split_disjoint),
        "all_training_releases_precede_test": strict_temporal,
        "training_releases": TRAIN_RELEASE_COMMITS,
        "test_releases": TEST_RELEASE_COMMITS,
        "training_samples": int(train_rows["total_samples"].sum()),
        "training_defects": int(train_rows["defective_samples"].sum()),
        "training_defect_percentage": float(train_rows["defective_samples"].sum() * 100 / train_rows["total_samples"].sum()),
        "test_samples": int(test_rows["total_samples"].sum()),
        "test_defects": int(test_rows["defective_samples"].sum()),
        "test_defect_percentage": float(test_rows["defective_samples"].sum() * 100 / test_rows["total_samples"].sum()),
        "retained_label_mismatches": int(frame["retained_label_mismatches"].sum()),
        "unmapped_record_count": len(unmapped),
        "unmapped_records": unmapped,
        "feature_columns_exclude_target": "isDefective" not in FEATURE_COLUMNS,
        "feature_columns": FEATURE_COLUMNS,
    }
    _atomic_json(audit, output_dir / "dataset_temporal_audit.json")
    return audit


def _calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> Dict[str, Any]:
    has_positive = bool(np.any(y_true == 1))
    has_both_classes = len(np.unique(y_true)) == 2
    if has_positive:
        precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_prob)
        pr_curve = {"precision": precision_curve.tolist(), "recall": recall_curve.tolist()}
        trap_pr_auc = float(auc(recall_curve, precision_curve))
        average_precision = float(average_precision_score(y_true, y_prob))
    else:
        pr_curve = None
        trap_pr_auc = None
        average_precision = None
    if has_both_classes:
        false_positive_rate, true_positive_rate, _ = roc_curve(y_true, y_prob)
        roc_curve_values = {"fpr": false_positive_rate.tolist(), "tpr": true_positive_rate.tolist()}
    else:
        roc_curve_values = None
    return {
        "Accuracy": float(accuracy_score(y_true, y_pred)),
        "Balanced_Accuracy": float(balanced_accuracy_score(y_true, y_pred)) if has_both_classes else None,
        "Precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "Recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "F1_Score": float(f1_score(y_true, y_pred, zero_division=0)),
        "ROC_AUC": float(roc_auc_score(y_true, y_prob)) if has_both_classes else None,
        "PR_AUC": average_precision,
        "Average_Precision": average_precision,
        "PR_AUC_trapezoidal": trap_pr_auc,
        "ConfusionMatrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "ROC_Curve": roc_curve_values,
        "PR_Curve": pr_curve,
    }


def run_model_audit(audit_dir: Path) -> Dict[str, Any]:
    output_dir = audit_dir / "models"
    output_dir.mkdir(parents=True, exist_ok=True)
    X_test = pd.read_csv(PROCESSED_DIR / "X_test.csv")
    y_test = pd.read_csv(PROCESSED_DIR / "y_test.csv").iloc[:, 0].to_numpy(dtype=int)
    if list(X_test.columns) != FEATURE_COLUMNS:
        raise ValueError("Saved X_test feature order differs from FEATURE_COLUMNS")

    saved_results = json.loads((RESULTS_DIR / "evaluation_metrics.json").read_text(encoding="utf-8"))
    rows = []
    comparisons = []
    for model_name in ("LogisticRegression", "DecisionTree", "RandomForest"):
        for feature_set in ("static", "combined"):
            selected_features = STATIC_FEATURES if feature_set == "static" else FEATURE_COLUMNS
            model_path = MODELS_DIR / f"{model_name}_{feature_set}.pkl"
            model = joblib.load(model_path)
            X = X_test[selected_features]
            prediction = model.predict(X).astype(int)
            probability = model.predict_proba(X)[:, 1]
            metrics = _calculate_metrics(y_test, prediction, probability)
            actual_positive_scores = probability[y_test == 1]
            actual_negative_scores = probability[y_test == 0]
            threshold_predictions = (probability >= 0.5).astype(int)
            persisted = saved_results[model_name][feature_set]
            metric_deltas = {}
            for key in ("Accuracy", "Balanced_Accuracy", "Precision", "Recall", "F1_Score", "ROC_AUC", "PR_AUC", "Average_Precision", "PR_AUC_trapezoidal"):
                metric_deltas[key] = abs(metrics[key] - float(persisted[key]))
            matrix_match = metrics["ConfusionMatrix"] == persisted["ConfusionMatrix"]
            rows.append({
                "model": model_name,
                "feature_set": feature_set,
                **{key: metrics[key] for key in ("Accuracy", "Balanced_Accuracy", "Precision", "Recall", "F1_Score", "ROC_AUC", "PR_AUC", "PR_AUC_trapezoidal", "Average_Precision")},
                "TN": metrics["ConfusionMatrix"][0][0],
                "FP": metrics["ConfusionMatrix"][0][1],
                "FN": metrics["ConfusionMatrix"][1][0],
                "TP": metrics["ConfusionMatrix"][1][1],
                "predicted_positive": int(prediction.sum()),
                "predictions_match_probability_threshold": bool(np.array_equal(prediction, threshold_predictions)),
                "predicted_true_positives": int(((prediction == 1) & (y_test == 1)).sum()),
                "predicted_false_positives": int(((prediction == 1) & (y_test == 0)).sum()),
                "positive_probability_min": float(probability.min()),
                "positive_probability_max": float(probability.max()),
                "max_score_for_actual_defect": float(actual_positive_scores.max()) if len(actual_positive_scores) else None,
                "max_score_for_actual_non_defect": float(actual_negative_scores.max()) if len(actual_negative_scores) else None,
                "saved_metrics_match": max(metric_deltas.values()) <= 1e-12 and matrix_match,
                "max_saved_metric_absolute_delta": max(metric_deltas.values()),
                "confusion_matrix_matches": matrix_match,
                "threshold_used_for_predict": 0.5,
            })
            comparisons.append({"model": model_name, "feature_set": feature_set,
                                "metric_deltas": metric_deltas, "confusion_matrix_matches": matrix_match})

    majority = DummyClassifier(strategy="most_frequent").fit(np.zeros((len(y_test), 1)), y_test)
    baseline_prediction = majority.predict(np.zeros((len(y_test), 1))).astype(int)
    baseline_probability = np.zeros(len(y_test), dtype=float)
    baseline_metrics = _calculate_metrics(y_test, baseline_prediction, baseline_probability)
    baseline_row = {
        "model": "MajorityClassBaseline",
        "feature_set": "none",
        **{key: baseline_metrics[key] for key in ("Accuracy", "Balanced_Accuracy", "Precision", "Recall", "F1_Score", "ROC_AUC", "PR_AUC", "PR_AUC_trapezoidal", "Average_Precision")},
        "TN": baseline_metrics["ConfusionMatrix"][0][0],
        "FP": baseline_metrics["ConfusionMatrix"][0][1],
        "FN": baseline_metrics["ConfusionMatrix"][1][0],
        "TP": baseline_metrics["ConfusionMatrix"][1][1],
        "predicted_positive": int(baseline_prediction.sum()),
        "positive_probability_min": 0.0,
        "positive_probability_max": 0.0,
        "saved_metrics_match": None,
        "max_saved_metric_absolute_delta": None,
        "confusion_matrix_matches": None,
        "threshold_used_for_predict": 0.5,
    }
    rows.append(baseline_row)
    frame = pd.DataFrame(rows)
    _atomic_csv(frame, output_dir / "model_evaluation_audit.csv")

    explanation_paths = [
        RESULTS_DIR / "logistic_regression_combined_feature_coefficients.csv",
        RESULTS_DIR / "logistic_regression_combined_shap_values.npy",
        RESULTS_DIR / "logistic_regression_combined_shap_base_values.npy",
        RESULTS_DIR / "logistic_regression_combined_shap_X_sample.csv",
        RESULTS_DIR / "logistic_regression_combined_shap_background.csv",
        RESULTS_DIR / "logistic_regression_combined_explanation_metadata.json",
    ]
    explanation_hashes_before = {path.name: _sha256(path) for path in explanation_paths}
    from src.models.explain import generate_explanations
    generate_explanations()
    explanation_hashes_after = {path.name: _sha256(path) for path in explanation_paths}

    # Verify transformation and persistence without refitting models.
    scaler = joblib.load(PROCESSED_DIR / "scaler.pkl")
    medians = json.loads((PROCESSED_DIR / "imputer_medians.json").read_text(encoding="utf-8"))
    raw_test = pd.concat([
        pd.read_csv(DERIVED_DIR / f"dataset-{commit}.csv")
        for commit in TEST_RELEASE_COMMITS
    ], ignore_index=True)[FEATURE_COLUMNS]
    transformed = scaler.transform(raw_test.fillna(medians))
    preprocessed_delta = float(np.max(np.abs(transformed - X_test.to_numpy())))
    output = {
        "saved_metrics_match_recalculation": all(row["saved_metrics_match"] for row in rows if row["model"] != "MajorityClassBaseline"),
        "saved_comparisons": comparisons,
        "majority_class_baseline": baseline_row,
        "test_rows": len(y_test),
        "test_label_distribution": {str(key): int(value) for key, value in pd.Series(y_test).value_counts().items()},
        "threshold_selection_implemented": False,
        "decision_threshold": 0.5,
        "saved_PR_AUC_definition": "PR_AUC is sklearn average_precision_score. PR_AUC_trapezoidal is separately reported as auc(recall, precision) over sklearn precision_recall_curve points.",
        "explainability_outputs_reproducible": explanation_hashes_before == explanation_hashes_after,
        "explainability_hashes_before": explanation_hashes_before,
        "explainability_hashes_after": explanation_hashes_after,
        "saved_scaler_feature_count": int(scaler.n_features_in_),
        "saved_scaler_feature_names": list(getattr(scaler, "feature_names_in_", [])),
        "imputer_feature_names_match": list(medians) == FEATURE_COLUMNS,
        "saved_preprocessing_max_absolute_difference_from_test_matrix": preprocessed_delta,
        "model_paths_loadable": all((MODELS_DIR / f"{name}_{feature}.pkl").is_file()
                                     for name in ("LogisticRegression", "DecisionTree", "RandomForest")
                                     for feature in ("static", "combined")),
        "evaluation_source_uses_model_predict_default_threshold": True,
    }
    _atomic_json(output, output_dir / "model_reproducibility_audit.json")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT_DIR)
    parser.add_argument("--commits", nargs="*", default=None, help="Limit static audit to these release hashes")
    parser.add_argument("--force", action="store_true", help="Recompute completed release audits")
    parser.add_argument("--static-only", action="store_true", help="Run only the resumable static parity audit")
    parser.add_argument("--skip-static", action="store_true", help="Run non-static audits only")
    args = parser.parse_args()
    audit_dir = args.audit_dir.resolve()

    results: Dict[str, Any] = {}
    results["parser_construct_probes"] = run_parser_construct_probes(audit_dir)
    if not args.skip_static:
        results["static"] = run_static_audit(audit_dir, args.commits, args.force)
    if not args.static_only:
        results["git_evolution"] = run_git_fixture_audit(audit_dir)
        results["dataset"] = run_dataset_audit(audit_dir)
        results["models"] = run_model_audit(audit_dir)
    _atomic_json(results, audit_dir / "audit_run_summary.json")
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()