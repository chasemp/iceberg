import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx


def get_current_head_hash(owner: str, name: str) -> str | None:
    """Get the current HEAD commit hash without cloning.

    Returns the short hash (8 chars) of the current HEAD commit.
    """
    try:
        # Use git ls-remote to get HEAD hash without cloning
        result = subprocess.run(
            ["git", "ls-remote", f"https://github.com/{owner}/{name}.git", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout:
            # Output format: "hash\tHEAD"
            hash_full = result.stdout.split()[0]
            return hash_full[:8]  # Return short hash

        return None
    except Exception:
        return None


def get_latest_published_version(owner: str, name: str) -> str | None:
    """Get the latest published version (git tag) for a repository.

    Returns the latest semver-like tag, or None if no tags found.
    """
    try:
        # Use GitHub API to get latest release
        url = f"https://api.github.com/repos/{owner}/{name}/releases/latest"
        response = httpx.get(url, timeout=10.0, follow_redirects=True)

        if response.status_code == 200:
            data: dict[str, Any] = response.json()
            tag: Any = data.get("tag_name")
            if isinstance(tag, str):
                return tag

        # Fallback: try to get tags via git ls-remote
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "--sort=-v:refname", f"https://github.com/{owner}/{name}.git"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout:
            # Parse first tag from output
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "refs/tags/" in line and "^{}" not in line:
                    parts = line.split("refs/tags/")
                    if len(parts) > 1:
                        tag_name: str = parts[1]
                        return tag_name

        return None
    except Exception:
        return None


def clone_repository(
    owner: str,
    name: str,
    target_dir: Path | None = None,
    ref: str | None = None,
) -> dict[str, Any] | None:
    """Clone a GitHub repository and return timing metadata.

    Args:
        owner: Repository owner
        name: Repository name
        target_dir: Target directory for clone
        ref: Git ref (branch/tag) to checkout. If None, uses default branch
    """
    try:
        repo_url = f"https://github.com/{owner}/{name}.git"

        if target_dir is None:
            target_dir = Path(tempfile.mkdtemp())

        start_time = time.time()

        clone_cmd = ["git", "clone", "--depth", "1"]
        if ref:
            clone_cmd.extend(["--branch", ref])
        clone_cmd.extend([repo_url, str(target_dir)])

        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        duration = time.time() - start_time

        if result.returncode != 0:
            return None

        # Get the actual commit hash
        commit_hash_result = subprocess.run(
            ["git", "-C", str(target_dir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        commit_hash = commit_hash_result.stdout.strip() if commit_hash_result.returncode == 0 else None

        return {
            "duration_seconds": duration,
            "repo_url": repo_url,
            "ref": ref or "HEAD",
            "commit_hash": commit_hash,
        }
    except Exception:
        return None


def count_repo_loc(repo_dir: Path) -> dict[str, Any] | None:
    """Count lines of code in a repository with timing data."""
    try:
        start_time = time.time()

        total_lines = 0

        # Common code file extensions
        code_extensions = {
            ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
            ".py", ".pyi",
            ".rs",
            ".go",
            ".java",
            ".c", ".cpp", ".h", ".hpp",
            ".rb",
            ".php",
            ".swift",
            ".kt", ".kts",
            ".cs",
            ".scala",
            ".clj", ".cljs",
            ".sh", ".bash",
        }

        for file_path in repo_dir.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix not in code_extensions:
                continue

            # Skip common non-source directories
            skip_dirs = {
                ".git", "node_modules", ".venv", "venv", "env",
                "__pycache__", ".pytest_cache", ".mypy_cache",
                "vendor", "deps", "target", "build", "dist",
                "test", "tests", "__tests__", "spec", "specs",
            }

            if any(part in skip_dirs for part in file_path.parts):
                continue

            try:
                content = file_path.read_text(errors="ignore")
                lines = content.split("\n")

                # Count non-empty, non-comment lines (simple heuristic)
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith(("#", "//", "/*", "*", "*/", "<!--")):
                        total_lines += 1
            except Exception:
                continue

        duration = time.time() - start_time

        return {
            "loc": total_lines,
            "duration_seconds": duration,
        }
    except Exception:
        return None


def get_github_project_loc(
    owner: str,
    name: str,
    cache_dir: Path | None = None,
    ref: str | None = None,
) -> dict[str, Any] | None:
    """Get LoC for a GitHub project by cloning and analyzing it.

    Args:
        owner: Repository owner
        name: Repository name
        cache_dir: Cache directory (not used yet for project LoC)
        ref: Git ref (branch/tag) to analyze. If None, uses default branch
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Clone repository
            clone_result = clone_repository(owner, name, target_dir=temp_path, ref=ref)
            if not clone_result:
                return None

            # Count LoC
            count_result = count_repo_loc(temp_path)
            if not count_result:
                return None

            return {
                "loc": count_result["loc"],
                "source": "github_clone",
                "metadata": {
                    "repo_url": clone_result["repo_url"],
                    "ref": clone_result["ref"],
                    "commit_hash": clone_result.get("commit_hash"),
                    "clone_duration_seconds": clone_result["duration_seconds"],
                    "count_duration_seconds": count_result["duration_seconds"],
                },
            }
    except Exception:
        return None
