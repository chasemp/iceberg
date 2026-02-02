from pathlib import Path

import pytest


def test_save_tracked_repo(tmp_path: Path) -> None:
    """Test saving a tracked repository."""
    from iceberg.tracking import save_tracked_repo

    save_tracked_repo("facebook", "react", cache_dir=tmp_path)

    tracked_file = tmp_path / "tracked.json"
    assert tracked_file.exists()

    import json
    data = json.loads(tracked_file.read_text())
    assert "repositories" in data
    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["owner"] == "facebook"
    assert data["repositories"][0]["repo"] == "react"


def test_load_tracked_repos(tmp_path: Path) -> None:
    """Test loading tracked repositories."""
    from iceberg.tracking import save_tracked_repo, load_tracked_repos

    save_tracked_repo("facebook", "react", cache_dir=tmp_path)
    save_tracked_repo("microsoft", "vscode", cache_dir=tmp_path)

    repos = load_tracked_repos(cache_dir=tmp_path)

    assert len(repos) == 2
    assert repos[0]["owner"] == "facebook"
    assert repos[1]["owner"] == "microsoft"


def test_remove_tracked_repo(tmp_path: Path) -> None:
    """Test removing a tracked repository."""
    from iceberg.tracking import save_tracked_repo, remove_tracked_repo, load_tracked_repos

    save_tracked_repo("facebook", "react", cache_dir=tmp_path)
    save_tracked_repo("microsoft", "vscode", cache_dir=tmp_path)

    remove_tracked_repo("facebook", "react", cache_dir=tmp_path)

    repos = load_tracked_repos(cache_dir=tmp_path)
    assert len(repos) == 1
    assert repos[0]["owner"] == "microsoft"


def test_is_repo_tracked(tmp_path: Path) -> None:
    """Test checking if a repo is tracked."""
    from iceberg.tracking import save_tracked_repo, is_repo_tracked

    save_tracked_repo("facebook", "react", cache_dir=tmp_path)

    assert is_repo_tracked("facebook", "react", cache_dir=tmp_path)
    assert not is_repo_tracked("microsoft", "vscode", cache_dir=tmp_path)
