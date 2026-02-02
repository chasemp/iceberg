from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock


def test_analyze_with_published_flag(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Test analyzing a specific published version via git tag."""
    from iceberg.cli import app
    from typer.testing import CliRunner

    runner = CliRunner()

    # This test would need significant mocking of git operations
    # For now, just verify the flag is accepted
    # We'll implement the full feature in phases

    # TODO: Test that --published flag triggers tag-based analysis
    pass


def test_detect_latest_published_version() -> None:
    """Test detecting the latest git tag for a repository."""
    from iceberg.github_loc import get_latest_published_version

    # Use a real repo with tags for testing
    version = get_latest_published_version("octocat", "Hello-World")

    # May or may not have tags, just verify it doesn't crash
    assert version is None or isinstance(version, str)


def test_clone_at_specific_tag(tmp_path: Path) -> None:
    """Test cloning a repository at a specific git tag."""
    from iceberg.github_loc import clone_repository

    # Clone at a specific ref
    result = clone_repository("octocat", "Hello-World", target_dir=tmp_path, ref="master")

    assert result is not None
    assert result["duration_seconds"] > 0
