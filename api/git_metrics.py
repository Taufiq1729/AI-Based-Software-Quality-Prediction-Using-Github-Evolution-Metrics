import os
import re
import subprocess
from collections import defaultdict
from typing import Dict, Any, Set, List, Optional
import git

class GitMetricsMiner:
    """
    Extracts Git evolution metrics for Java files:
    1. Code Churn (lines added + deleted)
    2. Revision Count (number of commits modifying the file)
    3. Developer Count (unique commit authors modifying the file)

    Preserves history across renames and provides repository-wide statistics.
    """

    @staticmethod
    def _parse_rename(path_str: str) -> str:
        """
        Normalizes Git rename syntax like 'path/{old => new}/File.java' or 'old.java => new.java'
        to the target (new) file path.
        """
        if "=>" not in path_str:
            return path_str.strip()

        # Handle '{old => new}'
        match_brace = re.search(r'^(.*?)\{(?:.*?)\s*=>\s*(.*?)\}(.*)$', path_str)
        if match_brace:
            prefix, new_mid, suffix = match_brace.groups()
            cleaned = (prefix + new_mid + suffix).replace("//", "/").strip()
            return cleaned

        # Handle 'old => new'
        parts = path_str.split("=>")
        if len(parts) == 2:
            return parts[1].strip()

        return path_str.strip()

    @staticmethod
    def mine_repository_evolution(
        repo_dir: str,
        target_files: Optional[Set[str]] = None,
        max_commits: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Mines commit history using high-performance git log streaming.
        Returns:
            - file_metrics: {relative_path: {'code_churn': int, 'revision_count': int, 'developer_count': int}}
            - repo_summary: {total_commits, total_developers, first_commit_date, latest_commit_date, total_churn}
        """
        file_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "code_churn": 0,
            "revision_count": 0,
            "developers": set()
        })

        all_repo_developers: Set[str] = set()
        total_commits = 0
        total_repo_churn = 0
        first_commit_date = None
        latest_commit_date = None

        cmd = [
            "git", "log",
            "--numstat",
            "--pretty=format:COMMIT_META:%H|%an|%ae|%at"
        ]
        if max_commits and max_commits > 0:
            cmd.extend(["-n", str(max_commits)])

        try:
            process = subprocess.Popen(
                cmd,
                cwd=repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            current_author = None
            current_email = None

            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue

                if line.startswith("COMMIT_META:"):
                    total_commits += 1
                    meta = line[len("COMMIT_META:"):].split("|")
                    if len(meta) >= 4:
                        _, author_name, author_email, timestamp = meta[:4]
                        current_email = (author_email.lower().strip() if author_email else author_name.strip()) or "unknown"
                        all_repo_developers.add(current_email)
                        
                        if latest_commit_date is None and timestamp.isdigit():
                            latest_commit_date = int(timestamp)
                        if timestamp.isdigit():
                            first_commit_date = int(timestamp)
                    continue

                # Numstat lines: <added> <deleted> <filename>
                parts = line.split(maxsplit=2)
                if len(parts) == 3:
                    added_str, deleted_str, raw_filepath = parts
                    # Binary files have '-' for added/deleted
                    added = int(added_str) if added_str.isdigit() else 0
                    deleted = int(deleted_str) if deleted_str.isdigit() else 0
                    churn = added + deleted

                    normalized_path = GitMetricsMiner._parse_rename(raw_filepath)
                    # Normalize path separators to forward slash
                    normalized_path = normalized_path.replace("\\", "/")

                    if normalized_path.endswith(".java"):
                        # If target_files set provided, match against it or base relative path
                        file_stats[normalized_path]["code_churn"] += churn
                        file_stats[normalized_path]["revision_count"] += 1
                        if current_email:
                            file_stats[normalized_path]["developers"].add(current_email)

                    total_repo_churn += churn

            process.wait()

        except Exception as e:
            # Fallback using GitPython if subprocess fails
            return GitMetricsMiner._fallback_gitpython(repo_dir, target_files)

        # Convert sets of developers into counts
        formatted_files: Dict[str, Dict[str, int]] = {}
        for path, data in file_stats.items():
            formatted_files[path] = {
                "code_churn": data["code_churn"],
                "revision_count": data["revision_count"],
                "developer_count": len(data["developers"])
            }

        repo_summary = {
            "total_commits": total_commits,
            "total_developers": len(all_repo_developers),
            "total_churn": total_repo_churn,
            "first_commit_timestamp": first_commit_date,
            "latest_commit_timestamp": latest_commit_date
        }

        return {
            "file_metrics": formatted_files,
            "repo_summary": repo_summary
        }

    @staticmethod
    def _fallback_gitpython(
        repo_dir: str,
        target_files: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Fallback mining method using GitPython.
        """
        file_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "code_churn": 0,
            "revision_count": 0,
            "developers": set()
        })
        all_developers = set()
        total_commits = 0

        try:
            repo = git.Repo(repo_dir)
            for commit in repo.iter_commits(max_count=1000):
                total_commits += 1
                author = commit.author.email or commit.author.name or "unknown"
                all_developers.add(author)

                if commit.parents:
                    diffs = commit.parents[0].diff(commit, create_patch=True)
                    for d in diffs:
                        path = (d.b_path or d.a_path or "").replace("\\", "/")
                        if path.endswith(".java"):
                            churn = 0
                            if d.diff:
                                lines = d.diff.decode('utf-8', errors='ignore').splitlines()
                                churn = sum(1 for l in lines if (l.startswith('+') or l.startswith('-')) and not (l.startswith('+++') or l.startswith('---')))
                            file_stats[path]["code_churn"] += churn
                            file_stats[path]["revision_count"] += 1
                            file_stats[path]["developers"].add(author)
        except Exception:
            pass

        formatted = {}
        for path, data in file_stats.items():
            formatted[path] = {
                "code_churn": data["code_churn"],
                "revision_count": data["revision_count"],
                "developer_count": len(data["developers"])
            }

        return {
            "file_metrics": formatted,
            "repo_summary": {
                "total_commits": total_commits,
                "total_developers": len(all_developers),
                "total_churn": sum(d["code_churn"] for d in formatted.values())
            }
        }

