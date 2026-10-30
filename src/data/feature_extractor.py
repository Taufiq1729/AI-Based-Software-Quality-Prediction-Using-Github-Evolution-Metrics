"""
Authoritative Shared Feature Extractor Pipeline.
Defines the single source of truth for:
- 12 Java Static Metrics
- 3 Git Evolution Metrics
- 15-Feature Schema and Exact Column Order
- Consistent Extraction for both Training and Scanning Pipelines
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd
import numpy as np

from src.analyzers.java_analyzer import (
    analyze_java_file,
    analyze_java_source,
    build_repository_context
)
from src.data.git_miner import (
    mine_file_history,
    mine_repository_evolution,
    _normalize_path
)

logger = logging.getLogger(__name__)

# 12 Java Static Metrics (Contract)
STATIC_FEATURES: List[str] = [
    "LOC",
    "WMC",
    "DIT",
    "NOC",
    "RFC",
    "LCOM5",
    "CBO",
    "NPA",
    "NPM",
    "NLE",
    "CBOI",
    "CD"
]

# 3 Git Evolution Metrics (Contract)
EVOLUTION_FEATURES: List[str] = [
    "code_churn",
    "revision_count",
    "developer_count"
]

# The authoritative 15-feature schema in exact required order
FEATURE_COLUMNS: List[str] = STATIC_FEATURES + EVOLUTION_FEATURES


def validate_feature_vector(features: Union[Dict[str, Any], pd.DataFrame, pd.Series]) -> pd.DataFrame:
    """
    Validates that:
    1. All 15 required features exist.
    2. No missing values or non-numeric values.
    3. Returns a DataFrame with columns in exact FEATURE_COLUMNS order.
    Throws ValueError if schema is violated.
    """
    if isinstance(features, dict):
        df = pd.DataFrame([features])
    elif isinstance(features, pd.Series):
        df = pd.DataFrame([features.to_dict()])
    elif isinstance(features, pd.DataFrame):
        df = features.copy()
    else:
        raise ValueError(f"Unsupported features type: {type(features)}")

    missing = [col for col in FEATURE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Feature vector is missing required features: {missing}. Expected exactly: {FEATURE_COLUMNS}")

    # Reorder strictly according to authoritative schema
    df_ordered = df[FEATURE_COLUMNS].copy()

    # Verify numeric conversion
    for col in FEATURE_COLUMNS:
        df_ordered[col] = pd.to_numeric(df_ordered[col], errors='coerce')
        if df_ordered[col].isnull().any():
            raise ValueError(f"Feature '{col}' contains non-numeric or null values.")

    return df_ordered


def extract_file_features(file_path: str,
                          repo_path: Optional[str] = None,
                          project_context: Optional[Dict[str, Any]] = None,
                          mined_evolution: Optional[Dict[str, Dict[str, int]]] = None,
                          target_class_name: Optional[str] = None,
                          line_range: Optional[Tuple[int, int]] = None,
                          to_commit: Optional[str] = None) -> Dict[str, float]:
    """
    Extracts all 15 real metrics (12 static + 3 evolution) for a Java file/class.
    Does NOT use mock or synthetic data.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Java file not found: {file_path}")

    # 1. Real Static Analysis using authoritative Java analyzer
    static_metrics = analyze_java_file(
        file_path=file_path,
        target_class_name=target_class_name,
        line_range=line_range,
        project_context=project_context
    )

    # 2. Real Rename-Aware Git Evolution Mining
    if repo_path and os.path.exists(repo_path):
        if mined_evolution is not None:
            rel_path = os.path.relpath(file_path, repo_path)
            norm_rel = _normalize_path(rel_path)
            evo_metrics = mined_evolution.get(norm_rel)
            if not evo_metrics:
                # Suffix / prefix fallback matching
                for p, s in mined_evolution.items():
                    if p.endswith(norm_rel) or norm_rel.endswith(p):
                        evo_metrics = s
                        break
            if not evo_metrics:
                evo_metrics = mine_file_history(repo_path, file_path, to_commit=to_commit)
        else:
            evo_metrics = mine_file_history(repo_path, file_path, to_commit=to_commit)
    else:
        evo_metrics = {"code_churn": 0, "revision_count": 0, "developer_count": 0}

    combined: Dict[str, float] = {}
    for col in STATIC_FEATURES:
        combined[col] = float(static_metrics.get(col, 0.0))

    for col in EVOLUTION_FEATURES:
        combined[col] = float(evo_metrics.get(col, 0))

    return combined


def extract_repository_features(repo_path: str) -> pd.DataFrame:
    """
    Scans an entire cloned Git repository:
    1. Identifies all Java source files.
    2. Builds whole-repo context for inter-class metrics (DIT, NOC, CBOI).
    3. Mines rename-aware Git history for all files.
    4. Computes 15 real features for each file.
    5. Returns a DataFrame with 'file' path and all 15 FEATURE_COLUMNS in exact order.
    """
    if not os.path.exists(repo_path):
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    java_files = []
    for root, _, files in os.walk(repo_path):
        for f in files:
            if f.endswith(".java"):
                java_files.append(os.path.join(root, f))

    if not java_files:
        logger.warning(f"No Java source files found in {repo_path}")
        empty = pd.DataFrame(columns=["file", "class_name", "class_identity"] + FEATURE_COLUMNS)
        empty.attrs.update({
            "java_files_discovered": 0,
            "classes_discovered": 0,
            "classes_scored": 0,
            "context_parse_failures": [],
            "analysis_failures": [],
            "unresolved_project_references": 0,
            "unidentified_class_files": [],
        })
        return empty

    logger.info(f"Analyzing {len(java_files)} Java files in {repo_path}...")
    project_context = build_repository_context(repo_path)
    logger.info("Repository context built. Mining Git evolution history with rename tracking...")

    rel_files = [os.path.relpath(fpath, repo_path).replace("\\", "/") for fpath in java_files]
    mined_evolution = mine_repository_evolution(repo_path, target_files=rel_files)

    records = []
    analysis_failures = []
    for fpath in java_files:
        rel_path = os.path.relpath(fpath, repo_path).replace("\\", "/")
        try:
            feats = extract_file_features(
                file_path=fpath,
                repo_path=repo_path,
                project_context=project_context,
                mined_evolution=mined_evolution
            )
            feats["file"] = rel_path
            definitions = [
                definition for definition in project_context.get("class_definitions", {}).get(rel_path, [])
                if definition.get("kind") in ("ClassDeclaration", "InterfaceDeclaration")
            ]
            definitions.sort(key=lambda definition: (
                definition.get("kind") == "InterfaceDeclaration",
                definition.get("start_line", 0),
            ))
            candidates = [definition for definition in definitions if definition.get("is_top_level")]
            candidates = candidates or definitions
            primary = candidates[0] if candidates else None
            for definition in candidates:
                if "public" in definition.get("modifiers", []):
                    primary = definition
                    break
            feats["class_name"] = primary["name"] if primary else ""
            feats["class_identity"] = primary["identity"] if primary else ""
            records.append(feats)
        except Exception as e:
            logger.warning(f"Failed to extract features for {rel_path}: {e}")
            analysis_failures.append({"file": rel_path, "reason": f"{type(e).__name__}: {e}"})

    if not records:
        result = pd.DataFrame(columns=["file", "class_name", "class_identity"] + FEATURE_COLUMNS)
        result.attrs.update({
            "java_files_discovered": len(java_files),
            "classes_discovered": sum(len(v) for v in project_context.get("class_definitions", {}).values()),
            "classes_scored": 0,
            "files_scored": 0,
            "context_parse_failures": project_context.get("parse_failures", []),
            "analysis_failures": analysis_failures,
            "unresolved_project_references": len(project_context.get("unresolved_references", [])),
            "unidentified_class_files": [],
        })
        return result

    df = pd.DataFrame(records)
    ordered_cols = ["file", "class_name", "class_identity"] + FEATURE_COLUMNS
    result = df[ordered_cols]
    result.attrs.update({
        "java_files_discovered": len(java_files),
        "classes_discovered": sum(len(v) for v in project_context.get("class_definitions", {}).values()),
        "classes_scored": int(df["class_identity"].astype(str).ne("").sum()),
        "files_scored": len(records),
        "context_parse_failures": project_context.get("parse_failures", []),
        "analysis_failures": analysis_failures,
        "unresolved_project_references": len(project_context.get("unresolved_references", [])),
        "unidentified_class_files": [
            {
                "file": row["file"],
                "reason": next((failure["error"] for failure in project_context.get("parse_failures", [])
                                if failure["path"] == row["file"]),
                               "No uniquely resolved class/interface identity was available."),
            }
            for _, row in result.loc[result["class_identity"].astype(str).eq("")].iterrows()
        ],
    })
    return result
