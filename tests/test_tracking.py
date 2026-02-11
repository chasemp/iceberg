import json
from pathlib import Path

import pytest


def _write_repo_metadata(
    cache_dir: Path, owner: str, repo: str, stars: int = 100, categories: dict | None = None
) -> None:
    repos_dir = cache_dir / "repos" / owner
    repos_dir.mkdir(parents=True, exist_ok=True)
    data = {"owner": owner, "name": repo, "stars": stars, "categories": categories or {}}
    (repos_dir / f"{repo}.json").write_text(json.dumps(data))


def test_save_tracked_repo_adds_tracked_category(tmp_path: Path) -> None:
    """Tracking a repo adds 'tracked' to its categories in repo metadata."""
    from iceberg.tracking import save_tracked_repo

    _write_repo_metadata(tmp_path, "facebook", "react", stars=200000)

    save_tracked_repo("facebook", "react", cache_dir=tmp_path)

    repo_file = tmp_path / "repos" / "facebook" / "react.json"
    assert repo_file.exists()

    data = json.loads(repo_file.read_text())
    assert "tracked" in data["categories"]


def test_save_tracked_repo_creates_metadata_if_missing(tmp_path: Path) -> None:
    """Tracking a repo creates repo metadata if it doesn't exist yet."""
    from iceberg.tracking import save_tracked_repo

    save_tracked_repo("facebook", "react", cache_dir=tmp_path)

    repo_file = tmp_path / "repos" / "facebook" / "react.json"
    assert repo_file.exists()

    data = json.loads(repo_file.read_text())
    assert "tracked" in data["categories"]
    assert data["owner"] == "facebook"
    assert data["name"] == "react"


def test_save_tracked_repo_preserves_existing_categories(tmp_path: Path) -> None:
    """Tracking a repo preserves other discovery categories."""
    from iceberg.tracking import save_tracked_repo

    _write_repo_metadata(
        tmp_path, "facebook", "react", stars=200000,
        categories={"github-ranking-top-100-stars": "2026-02-09"},
    )

    save_tracked_repo("facebook", "react", cache_dir=tmp_path)

    data = json.loads((tmp_path / "repos" / "facebook" / "react.json").read_text())
    assert "tracked" in data["categories"]
    assert "github-ranking-top-100-stars" in data["categories"]


def test_load_tracked_repos_returns_repos_with_tracked_category(tmp_path: Path) -> None:
    """load_tracked_repos returns only repos with 'tracked' in categories."""
    from iceberg.tracking import load_tracked_repos

    _write_repo_metadata(
        tmp_path, "facebook", "react", stars=200000,
        categories={"tracked": "2026-02-09", "search": "2026-02-10"},
    )
    _write_repo_metadata(
        tmp_path, "microsoft", "vscode", stars=100000,
        categories={"search": "2026-02-10"},
    )

    repos = load_tracked_repos(cache_dir=tmp_path)

    assert len(repos) == 1
    assert repos[0]["owner"] == "facebook"
    assert repos[0]["repo"] == "react"


def test_load_tracked_repos_returns_empty_for_no_tracked(tmp_path: Path) -> None:
    from iceberg.tracking import load_tracked_repos

    _write_repo_metadata(tmp_path, "owner", "repo", categories={"search": "2026-02-10"})

    repos = load_tracked_repos(cache_dir=tmp_path)
    assert repos == []


def test_remove_tracked_repo_removes_tracked_category(tmp_path: Path) -> None:
    """Untracking a repo removes 'tracked' from categories but keeps others."""
    from iceberg.tracking import remove_tracked_repo

    _write_repo_metadata(
        tmp_path, "facebook", "react", stars=200000,
        categories={"tracked": "2026-02-09", "search": "2026-02-10"},
    )

    remove_tracked_repo("facebook", "react", cache_dir=tmp_path)

    data = json.loads((tmp_path / "repos" / "facebook" / "react.json").read_text())
    assert "tracked" not in data["categories"]
    assert "search" in data["categories"]


def test_is_repo_tracked_returns_true_for_tracked(tmp_path: Path) -> None:
    from iceberg.tracking import is_repo_tracked

    _write_repo_metadata(
        tmp_path, "facebook", "react",
        categories={"tracked": "2026-02-09"},
    )

    assert is_repo_tracked("facebook", "react", cache_dir=tmp_path) is True


def test_is_repo_tracked_returns_false_when_not_tracked(tmp_path: Path) -> None:
    from iceberg.tracking import is_repo_tracked

    _write_repo_metadata(
        tmp_path, "facebook", "react",
        categories={"search": "2026-02-10"},
    )

    assert is_repo_tracked("facebook", "react", cache_dir=tmp_path) is False


def test_is_repo_tracked_returns_false_when_repo_missing(tmp_path: Path) -> None:
    from iceberg.tracking import is_repo_tracked

    assert is_repo_tracked("nonexistent", "repo", cache_dir=tmp_path) is False
