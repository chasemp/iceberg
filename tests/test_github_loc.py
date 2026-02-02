from pathlib import Path

import pytest


def test_clone_repository_to_temp_dir(tmp_path: Path) -> None:
    """Test cloning a repository to a temporary directory."""
    from iceberg.github_loc import clone_repository

    # Use a small, fast-to-clone repo for testing
    result = clone_repository("octocat", "Hello-World", target_dir=tmp_path)

    assert result is not None
    assert "duration_seconds" in result
    assert result["duration_seconds"] > 0
    assert (tmp_path / ".git").exists()


def test_clone_repository_handles_invalid_repo(tmp_path: Path) -> None:
    """Test graceful handling of non-existent repository."""
    from iceberg.github_loc import clone_repository

    result = clone_repository("nonexistent", "fake-repo-xyz", target_dir=tmp_path)

    assert result is None


def test_count_loc_in_git_repo(tmp_path: Path) -> None:
    """Test counting LoC from a cloned repository."""
    from iceberg.github_loc import count_repo_loc

    # Create test files
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "main.py").write_text("""
def hello():
    return "world"

# Comment line
""")

    (src_dir / "utils.py").write_text("""
class Helper:
    def process(self):
        pass
""")

    result = count_repo_loc(tmp_path)

    assert result is not None
    assert "loc" in result
    assert "duration_seconds" in result
    assert result["loc"] > 0
    assert result["duration_seconds"] >= 0


def test_get_github_project_loc_full_workflow(tmp_path: Path) -> None:
    """Test full workflow of getting project LoC from GitHub."""
    from iceberg.github_loc import get_github_project_loc

    # Use octocat/Hello-World as it's small and stable
    result = get_github_project_loc("octocat", "Hello-World", cache_dir=tmp_path)

    assert result is not None
    assert result["loc"] >= 0  # Hello-World might not have code files, just verify it works
    assert result["source"] == "github_clone"
    assert "metadata" in result
    assert "clone_duration_seconds" in result["metadata"]
    assert "count_duration_seconds" in result["metadata"]
    assert "repo_url" in result["metadata"]
    assert result["metadata"]["clone_duration_seconds"] > 0  # Cloning takes time


def test_get_github_project_loc_handles_errors(tmp_path: Path) -> None:
    """Test graceful handling of clone/count errors."""
    from iceberg.github_loc import get_github_project_loc

    result = get_github_project_loc(
        "nonexistent", "fake-repo-xyz", cache_dir=tmp_path
    )

    assert result is None
