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
