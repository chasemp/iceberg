import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


def clone_repository(
    owner: str,
    name: str,
    target_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Clone a GitHub repository and return timing metadata."""
    try:
        repo_url = f"https://github.com/{owner}/{name}.git"

        if target_dir is None:
            target_dir = Path(tempfile.mkdtemp())

        start_time = time.time()

        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(target_dir)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        duration = time.time() - start_time

        if result.returncode != 0:
            return None

        return {
            "duration_seconds": duration,
            "repo_url": repo_url,
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
) -> dict[str, Any] | None:
    """Get LoC for a GitHub project by cloning and analyzing it."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Clone repository
            clone_result = clone_repository(owner, name, target_dir=temp_path)
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
                    "clone_duration_seconds": clone_result["duration_seconds"],
                    "count_duration_seconds": count_result["duration_seconds"],
                },
            }
    except Exception:
        return None
