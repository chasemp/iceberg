from pathlib import Path

import pytest


def test_save_project_loc_creates_versioned_cache(tmp_path: Path) -> None:
    """Test saving project LoC with version creates versioned cache entry."""
    from iceberg.cache import save_project_loc

    project_data = {
        "owner": "facebook",
        "repo": "react",
        "version": "v18.2.0",
        "loc": 15000,
        "source": "github_clone",
        "cached_at": "2026-02-02T12:00:00Z",
        "ref": "v18.2.0",
    }

    save_project_loc(project_data, cache_dir=tmp_path)

    cache_file = tmp_path / "projects" / "facebook" / "react" / "v18.2.0.json"
    assert cache_file.exists()


def test_load_project_loc_reads_versioned_cache(tmp_path: Path) -> None:
    """Test loading project LoC from versioned cache."""
    from iceberg.cache import load_project_loc, save_project_loc

    project_data = {
        "owner": "facebook",
        "repo": "react",
        "version": "v18.2.0",
        "loc": 15000,
        "source": "github_clone",
        "cached_at": "2026-02-02T12:00:00Z",
        "ref": "v18.2.0",
    }

    save_project_loc(project_data, cache_dir=tmp_path)

    loaded = load_project_loc("facebook", "react", "v18.2.0", cache_dir=tmp_path)

    assert loaded is not None
    assert loaded["loc"] == 15000
    assert loaded["version"] == "v18.2.0"


def test_load_project_loc_returns_none_when_missing(tmp_path: Path) -> None:
    """Test loading non-existent project LoC returns None."""
    from iceberg.cache import load_project_loc

    result = load_project_loc("nonexistent", "repo", "v1.0.0", cache_dir=tmp_path)

    assert result is None


def test_list_cached_project_versions(tmp_path: Path) -> None:
    """Test listing all cached versions for a project."""
    from iceberg.cache import list_project_versions, save_project_loc

    # Save multiple versions
    for version in ["v1.0.0", "v2.0.0", "v2.1.0"]:
        project_data = {
            "owner": "facebook",
            "repo": "react",
            "version": version,
            "loc": 15000,
            "source": "github_clone",
            "cached_at": "2026-02-02T12:00:00Z",
            "ref": version,
        }
        save_project_loc(project_data, cache_dir=tmp_path)

    versions = list_project_versions("facebook", "react", cache_dir=tmp_path)

    assert len(versions) == 3
    assert "v1.0.0" in versions
    assert "v2.0.0" in versions
    assert "v2.1.0" in versions


def test_load_repo_metadata_returns_metadata_when_exists(tmp_path: Path) -> None:
    """Test loading repository metadata when file exists."""
    from iceberg.cache import load_repo_metadata, save_repo_metadata
    from iceberg.models import DiscoveredRepo

    repo = DiscoveredRepo(
        name="react",
        owner="facebook",
        url="https://github.com/facebook/react",
        description="A JavaScript library for building user interfaces",
        language="JavaScript",
        stars=200000,
        source="trending-monthly",
        discovered_at="2026-02-12T12:00:00Z",
    )

    save_repo_metadata(repo, "trending-monthly", cache_dir=tmp_path)

    loaded = load_repo_metadata("facebook", "react", cache_dir=tmp_path)

    assert loaded is not None
    assert loaded["owner"] == "facebook"
    assert loaded["name"] == "react"
    assert loaded["stars"] == 200000


def test_load_repo_metadata_returns_none_when_missing(tmp_path: Path) -> None:
    """Test loading repository metadata returns None when file doesn't exist."""
    from iceberg.cache import load_repo_metadata

    result = load_repo_metadata("nonexistent", "repo", cache_dir=tmp_path)

    assert result is None


def test_load_repo_metadata_returns_none_on_json_decode_error(tmp_path: Path) -> None:
    """Test loading repository metadata returns None when JSON is corrupted."""
    from iceberg.cache import load_repo_metadata

    repo_dir = tmp_path / "repos" / "facebook"
    repo_dir.mkdir(parents=True)
    repo_file = repo_dir / "react.json"
    repo_file.write_text("{ invalid json }")

    result = load_repo_metadata("facebook", "react", cache_dir=tmp_path)

    assert result is None


def test_load_repo_metadata_returns_none_on_io_error(tmp_path: Path) -> None:
    """Test loading repository metadata returns None when file cannot be read."""
    from iceberg.cache import load_repo_metadata
    from unittest.mock import patch

    repo_dir = tmp_path / "repos" / "facebook"
    repo_dir.mkdir(parents=True)
    repo_file = repo_dir / "react.json"
    repo_file.write_text('{"owner": "facebook", "name": "react"}')

    with patch("pathlib.Path.read_text", side_effect=IOError("Permission denied")):
        result = load_repo_metadata("facebook", "react", cache_dir=tmp_path)

    assert result is None


def test_load_repo_metadata_typed_returns_model_when_exists(tmp_path: Path) -> None:
    """Test loading repository metadata as typed model."""
    from iceberg.cache import load_repo_metadata_typed, save_repo_metadata
    from iceberg.models import DiscoveredRepo

    repo = DiscoveredRepo(
        name="react",
        owner="facebook",
        url="https://github.com/facebook/react",
        description="A JavaScript library for building user interfaces",
        language="JavaScript",
        stars=200000,
        source="trending-monthly",
        discovered_at="2026-02-12T12:00:00Z",
    )

    save_repo_metadata(repo, "trending-monthly", cache_dir=tmp_path)

    loaded = load_repo_metadata_typed("facebook", "react", cache_dir=tmp_path)

    assert loaded is not None
    assert loaded.owner == "facebook"
    assert loaded.name == "react"
    assert loaded.stars == 200000
    assert "trending-monthly" in loaded.categories


def test_load_repo_metadata_typed_returns_none_when_missing(tmp_path: Path) -> None:
    """Test loading typed metadata returns None when file doesn't exist."""
    from iceberg.cache import load_repo_metadata_typed

    result = load_repo_metadata_typed("nonexistent", "repo", cache_dir=tmp_path)

    assert result is None


def test_load_repo_metadata_typed_returns_none_on_corrupted_data(tmp_path: Path) -> None:
    """Test loading typed metadata returns None when JSON is corrupted."""
    from iceberg.cache import load_repo_metadata_typed

    repo_dir = tmp_path / "repos" / "facebook"
    repo_dir.mkdir(parents=True)
    repo_file = repo_dir / "react.json"
    repo_file.write_text("{ invalid json }")

    result = load_repo_metadata_typed("facebook", "react", cache_dir=tmp_path)

    assert result is None


def test_save_repo_metadata_accepts_repository_metadata_model(tmp_path: Path) -> None:
    """Test save_repo_metadata accepts RepositoryMetadata model."""
    from iceberg.cache import load_repo_metadata_typed, save_repo_metadata
    from iceberg.models import RepositoryMetadata

    metadata = RepositoryMetadata(
        name="react",
        owner="facebook",
        url="https://github.com/facebook/react",
        description="A JavaScript library",
        language="JavaScript",
        stars=200000,
        categories={"trending-monthly": "2026-02-09", "search": "2026-02-10"},
        last_discovered="2026-02-10",
    )

    save_repo_metadata(metadata, "new-category", cache_dir=tmp_path)

    loaded = load_repo_metadata_typed("facebook", "react", cache_dir=tmp_path)

    assert loaded is not None
    assert "new-category" in loaded.categories
    assert "trending-monthly" in loaded.categories
    assert loaded.last_discovered == "2026-02-10"


def test_list_all_repos_typed_returns_models(tmp_path: Path) -> None:
    """Test listing all repositories as typed models."""
    from iceberg.cache import list_all_repos_typed, save_repo_metadata
    from iceberg.models import DiscoveredRepo

    repos = [
        DiscoveredRepo(
            name="repo1",
            owner="owner1",
            url="https://github.com/owner1/repo1",
            description="First repo",
            language="Python",
            stars=100,
            source="trending-monthly",
            discovered_at="2026-02-12T12:00:00Z",
        ),
        DiscoveredRepo(
            name="repo2",
            owner="owner2",
            url="https://github.com/owner2/repo2",
            description="Second repo",
            language="JavaScript",
            stars=200,
            source="search",
            discovered_at="2026-02-12T12:00:00Z",
        ),
    ]

    for repo in repos:
        save_repo_metadata(repo, repo.source, cache_dir=tmp_path)

    all_repos = list_all_repos_typed(cache_dir=tmp_path)

    assert len(all_repos) == 2
    names = {r.name for r in all_repos}
    assert names == {"repo1", "repo2"}
    assert all(hasattr(r, "categories") for r in all_repos)


def test_get_repos_by_category_typed_filters_by_category(tmp_path: Path) -> None:
    """Test getting repositories by category as typed models."""
    from iceberg.cache import get_repos_by_category_typed, save_repo_metadata
    from iceberg.models import DiscoveredRepo

    repos = [
        DiscoveredRepo(
            name="trending-repo",
            owner="owner1",
            url="https://github.com/owner1/trending-repo",
            description="Trending",
            language="Python",
            stars=1000,
            source="trending-monthly",
            discovered_at="2026-02-12T12:00:00Z",
        ),
        DiscoveredRepo(
            name="search-repo",
            owner="owner2",
            url="https://github.com/owner2/search-repo",
            description="Search result",
            language="JavaScript",
            stars=500,
            source="search",
            discovered_at="2026-02-12T12:00:00Z",
        ),
    ]

    for repo in repos:
        save_repo_metadata(repo, repo.source, cache_dir=tmp_path)

    trending_repos = get_repos_by_category_typed("trending-monthly", cache_dir=tmp_path)

    assert len(trending_repos) == 1
    assert trending_repos[0].name == "trending-repo"
    assert "trending-monthly" in trending_repos[0].categories
