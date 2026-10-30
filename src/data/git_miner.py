"""
Authoritative Git History Evolution Miner.
Extracts real, rename-aware Git evolution metrics for files and repositories:
- code_churn      : total lines added + total lines deleted across file history
- revision_count  : total commits/revisions modifying the file (following renames)
- developer_count : total distinct authors/developers modifying the file (following renames)
Strictly limits history mining up to target release commit to prevent temporal lookahead leakage.
"""

import os
import re
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, Set, List, Tuple

logger = logging.getLogger(__name__)


def _normalize_path(p: str) -> str:
    """Normalizes path to forward slashes and strips leading/trailing slashes."""
    return p.replace("\\", "/").strip("/").lower()


def _parse_rename_path(fpath: str) -> Optional[Tuple[str, str]]:
    """
    Parses git log --numstat rename syntax:
    - path/{old => new}/File.java -> (path/old/File.java, path/new/File.java)
    - {old => new}/File.java      -> (old/File.java, new/File.java)
    - old.java => new.java        -> (old.java, new.java)
    Returns (old_path, new_path) if rename detected, otherwise None.
    """
    if "=>" not in fpath:
        return None

    # Format: prefix/{old => new}/suffix
    brace_match = re.search(r'^(.*?)\{(.*?)\s*=>\s*(.*?)\}(.*)$', fpath)
    if brace_match:
        prefix, old_part, new_part, suffix = brace_match.groups()
        old_p = (prefix + old_part + suffix).replace("//", "/")
        new_p = (prefix + new_part + suffix).replace("//", "/")
        return old_p.strip(), new_p.strip()

    # Format: old => new
    arrow_match = re.search(r'^(.*?)\s*=>\s*(.*?)$', fpath)
    if arrow_match:
        return arrow_match.group(1).strip(), arrow_match.group(2).strip()

    return None


def _get_git_command_base(repo_path: str) -> List[str]:
    """Constructs the base git command for bare or work-tree repositories."""
    git_dir = repo_path
    if os.path.exists(os.path.join(repo_path, ".git")):
        git_dir = os.path.join(repo_path, ".git")

    cmd = ["git", f"--git-dir={git_dir}"]
    if not repo_path.endswith(".git") and os.path.exists(os.path.join(repo_path, ".git")):
        cmd.append(f"--work-tree={repo_path}")
    return cmd


def mine_file_history(repo_path: str, file_path: str, to_commit: Optional[str] = None) -> Dict[str, int]:
    """
    Mines real Git history for a single file using native git log --follow -M.
    Strictly follows file renames and moves across repository history.
    Limits mining up to to_commit (preventing temporal leakage).
    """
    rel_path = file_path
    if os.path.isabs(file_path):
        rel_path = os.path.relpath(file_path, repo_path)
    clean_rel = rel_path.replace("\\", "/").strip("/")

    cmd = _get_git_command_base(repo_path)
    cmd.extend(["log", "--follow", "-M", "--numstat", "--format=COMMIT:%H|%aE|%aN"])
    if to_commit:
        cmd.append(to_commit)
    else:
        cmd.append("HEAD")
    cmd.extend(["--", clean_rel])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=60)
        if proc.returncode == 0 and proc.stdout:
            revisions = 0
            churn = 0
            authors: Set[str] = set()

            for line in proc.stdout.splitlines():
                if line.startswith("COMMIT:"):
                    parts = line[7:].split("|")
                    email = parts[1].strip() if len(parts) > 1 and parts[1].strip() else ""
                    name = parts[2].strip() if len(parts) > 2 and parts[2].strip() else ""
                    author = email or name or "unknown"
                    authors.add(author)
                    revisions += 1
                elif "\t" in line:
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        try:
                            added = int(parts[0])
                            deleted = int(parts[1])
                            churn += (added + deleted)
                        except ValueError:
                            pass

            return {
                "code_churn": churn,
                "revision_count": revisions,
                "developer_count": len(authors)
            }
    except Exception as e:
        logger.debug(f"Native git log --follow failed for {clean_rel}: {e}")

    # Fallback return empty stats
    return {
        "code_churn": 0,
        "revision_count": 0,
        "developer_count": 0
    }


def mine_repository_evolution(repo_path: str,
                              to_commit: Optional[str] = None,
                              target_files: Optional[List[str]] = None) -> Dict[str, Dict[str, int]]:
    """
    Mines real Git evolution metrics for files up to an optional commit.
    Uses multi-threaded native git log --follow -M to guarantee exact rename tracking
    for every target file without temporal leakage.
    Returns:
        Dict mapping normalized relative file path -> {
            "code_churn": int,
            "revision_count": int,
            "developer_count": int
        }
    """
    # 1. Determine list of target files
    files_to_mine = []
    if target_files:
        files_to_mine = target_files
    else:
        # Discover files via git ls-tree or filesystem
        cmd = _get_git_command_base(repo_path)
        commit_ref = to_commit or "HEAD"
        cmd.extend(["ls-tree", "-r", "--name-only", commit_ref])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=30)
            if proc.returncode == 0 and proc.stdout:
                files_to_mine = [
                    line.strip() for line in proc.stdout.splitlines()
                    if line.strip().endswith(".java")
                ]
        except Exception:
            pass

        if not files_to_mine and os.path.exists(repo_path):
            for root, _, files in os.walk(repo_path):
                for f in files:
                    if f.endswith(".java"):
                        full_p = os.path.join(root, f)
                        files_to_mine.append(os.path.relpath(full_p, repo_path).replace("\\", "/"))

    if not files_to_mine:
        logger.warning(f"No files identified for evolution mining in {repo_path}")
        return {}

    logger.info(f"Mining rename-aware Git evolution for {len(files_to_mine)} files up to commit {to_commit or 'HEAD'}...")

    result: Dict[str, Dict[str, int]] = {}

    def _mine_single(rel_f: str) -> Tuple[str, Dict[str, int]]:
        stats = mine_file_history(repo_path, rel_f, to_commit=to_commit)
        return _normalize_path(rel_f), stats

    max_workers = min(16, max(4, (os.cpu_count() or 4) * 2))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for norm_path, stats in executor.map(_mine_single, files_to_mine):
            result[norm_path] = stats

    logger.info(f"Mined evolution metrics for {len(result)} files with rename tracking.")
    return result
