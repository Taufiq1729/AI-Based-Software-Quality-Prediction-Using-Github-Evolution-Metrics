import os
import re
import shutil
import tempfile
import subprocess
from typing import Dict, Any, Optional
import git

class GitHubService:
    GITHUB_URL_REGEX = re.compile(
        r'^(https?://)?(www\.)?github\.com/(?P<owner>[\w\.-]+)/(?P<repo>[\w\.-]+?)(?:\.git)?/?$'
    )

    @staticmethod
    def validate_url(url: str) -> Dict[str, Any]:
        """
        Validates whether a URL is a syntactically correct GitHub repository URL.
        """
        if not url or not isinstance(url, str):
            return {"valid": False, "error": "Repository URL cannot be empty."}
        
        url_clean = url.strip()
        match = GitHubService.GITHUB_URL_REGEX.match(url_clean)
        if not match:
            return {
                "valid": False,
                "error": "Invalid GitHub URL. Format must be: https://github.com/owner/repository"
            }
        
        owner = match.group("owner")
        repo = match.group("repo")
        normalized_url = f"https://github.com/{owner}/{repo}"
        
        return {
            "valid": True,
            "owner": owner,
            "repo": repo,
            "normalized_url": normalized_url
        }

    @staticmethod
    def check_repo_accessible(url: str) -> Dict[str, Any]:
        """
        Checks whether the repository is publicly reachable via git ls-remote.
        """
        val = GitHubService.validate_url(url)
        if not val["valid"]:
            return val
        
        norm_url = val["normalized_url"]
        try:
            # Quick check with git ls-remote with 10s timeout
            result = subprocess.run(
                ["git", "ls-remote", "--heads", norm_url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=12
            )
            if result.returncode != 0:
                err_text = result.stderr.strip() or "Repository not accessible"
                if "Authentication failed" in err_text or "not found" in err_text.lower():
                    return {
                        "valid": False,
                        "error": "Repository was not found or is private. Only public repositories are supported."
                    }
                return {
                    "valid": False,
                    "error": f"Failed to access repository: {err_text}"
                }
            
            # Check if remote has any branches
            if not result.stdout.strip():
                return {
                    "valid": False,
                    "error": "Repository appears to be empty (no branches found)."
                }
            
            return {
                "valid": True,
                "owner": val["owner"],
                "repo": val["repo"],
                "normalized_url": norm_url
            }
        except subprocess.TimeoutExpired:
            return {
                "valid": False,
                "error": "Connection timed out while trying to reach GitHub."
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Error verifying repository: {str(e)}"
            }

    @staticmethod
    def clone_repository(
        url: str,
        dest_dir: Optional[str] = None,
        max_commits: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Clones a public GitHub repository to a local directory for analysis.
        """
        validation = GitHubService.validate_url(url)
        if not validation["valid"]:
            raise ValueError(validation["error"])

        target_dir = dest_dir or tempfile.mkdtemp(prefix=f"sqam_{validation['repo']}_")
        norm_url = validation["normalized_url"]

        try:
            # Clone with single branch or full history for mining
            clone_args = [norm_url, target_dir]
            if max_commits and max_commits > 0:
                clone_args = ["--depth", str(max_commits)] + clone_args
            
            git.Repo.clone_from(norm_url, target_dir)
            repo = git.Repo(target_dir)

            # Get basic commit metadata
            total_commits = 0
            latest_commit_hash = None
            latest_commit_date = None
            try:
                commits = list(repo.iter_commits(max_count=2000))
                total_commits = len(commits)
                if commits:
                    latest_commit_hash = commits[0].hexsha[:8]
                    latest_commit_date = commits[0].committed_datetime.isoformat()
            except Exception:
                pass

            return {
                "success": True,
                "repo_dir": target_dir,
                "repo_name": validation["repo"],
                "owner": validation["owner"],
                "url": norm_url,
                "total_commits": total_commits,
                "latest_commit_hash": latest_commit_hash,
                "latest_commit_date": latest_commit_date
            }
        except git.GitCommandError as e:
            GitHubService.cleanup(target_dir)
            raise RuntimeError(f"Git clone error: {e.stderr or str(e)}")
        except Exception as e:
            GitHubService.cleanup(target_dir)
            raise RuntimeError(f"Failed to clone repository: {str(e)}")

    @staticmethod
    def cleanup(dir_path: str) -> None:
        """
        Safely deletes the cloned repository workspace.
        """
        if dir_path and os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path, ignore_errors=True)
            except Exception:
                pass

