from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests.factories import (
    create_discovered_repo,
    create_loc_metrics,
    create_package_identifier,
    create_trending_repo,
)


def test_save_trending_repos_creates_json_file(tmp_path: Path) -> None:
    from iceberg.cache import save_trending_repos

    repos = [
        create_trending_repo(name="repo1", owner="owner1"),
        create_trending_repo(name="repo2", owner="owner2"),
    ]

    save_trending_repos(repos, cache_dir=tmp_path)

    today = datetime.now(timezone.utc).date().isoformat()
    cache_file = tmp_path / "trending" / f"{today}.json"

    assert cache_file.exists()


def test_load_trending_repos_reads_json_file(tmp_path: Path) -> None:
    from iceberg.cache import load_trending_repos, save_trending_repos

    repos = [
        create_trending_repo(name="repo1", owner="owner1", stars=100),
        create_trending_repo(name="repo2", owner="owner2", stars=200),
    ]

    save_trending_repos(repos, cache_dir=tmp_path)
    loaded_repos = load_trending_repos(cache_dir=tmp_path)

    assert len(loaded_repos) == 2
    assert loaded_repos[0].name == "repo1"
    assert loaded_repos[0].stars == 100
    assert loaded_repos[1].name == "repo2"
    assert loaded_repos[1].stars == 200


def test_load_trending_repos_returns_none_when_missing(tmp_path: Path) -> None:
    from iceberg.cache import load_trending_repos

    loaded_repos = load_trending_repos(cache_dir=tmp_path)

    assert loaded_repos is None


def test_save_loc_metrics_creates_json_file(tmp_path: Path) -> None:
    from iceberg.cache import save_loc_metrics

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")
    metrics = create_loc_metrics(package=pkg, total_lines=5000)

    save_loc_metrics(metrics, cache_dir=tmp_path)

    cache_file = tmp_path / "loc" / "npm" / "react" / "18.2.0.json"

    assert cache_file.exists()


def test_load_loc_metrics_reads_json_file(tmp_path: Path) -> None:
    from iceberg.cache import load_loc_metrics, save_loc_metrics

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")
    metrics = create_loc_metrics(package=pkg, total_lines=5000, source="depsdev")

    save_loc_metrics(metrics, cache_dir=tmp_path)
    loaded_metrics = load_loc_metrics(pkg, cache_dir=tmp_path)

    assert loaded_metrics is not None
    assert loaded_metrics.total_lines == 5000
    assert loaded_metrics.source == "depsdev"
    assert loaded_metrics.package.name == "react"


def test_load_loc_metrics_returns_none_when_missing(tmp_path: Path) -> None:
    from iceberg.cache import load_loc_metrics

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")
    loaded_metrics = load_loc_metrics(pkg, cache_dir=tmp_path)

    assert loaded_metrics is None


def test_is_cache_fresh_returns_true_for_recent_cache(tmp_path: Path) -> None:
    from iceberg.cache import is_cache_fresh, save_trending_repos

    repos = [create_trending_repo()]
    save_trending_repos(repos, cache_dir=tmp_path)

    assert is_cache_fresh(cache_dir=tmp_path, max_age_days=7) is True


def test_is_cache_fresh_returns_false_when_missing(tmp_path: Path) -> None:
    from iceberg.cache import is_cache_fresh

    assert is_cache_fresh(cache_dir=tmp_path, max_age_days=7) is False


def test_is_cache_fresh_returns_false_for_old_cache(tmp_path: Path) -> None:
    from iceberg.cache import save_trending_repos

    repos = [create_trending_repo()]

    trending_dir = tmp_path / "trending"
    trending_dir.mkdir(parents=True)

    old_date = (datetime.now(timezone.utc) - timedelta(days=10)).date().isoformat()
    old_file = trending_dir / f"{old_date}.json"

    from iceberg.cache import save_trending_repos

    save_trending_repos(repos, cache_dir=tmp_path)

    cache_file = trending_dir / f"{datetime.now(timezone.utc).date().isoformat()}.json"
    cache_file.rename(old_file)

    from iceberg.cache import is_cache_fresh

    assert is_cache_fresh(cache_dir=tmp_path, max_age_days=7) is False


def test_save_dependencies_creates_json_file(tmp_path: Path) -> None:
    from iceberg.cache import save_dependencies

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")
    deps = [
        create_package_identifier(system="npm", name="dep1", version="1.0.0"),
        create_package_identifier(system="npm", name="dep2", version="2.0.0"),
    ]

    save_dependencies(pkg, deps, cache_dir=tmp_path)

    cache_file = tmp_path / "dependencies" / "npm" / "react" / "18.2.0.json"

    assert cache_file.exists()


def test_load_dependencies_reads_json_file(tmp_path: Path) -> None:
    from iceberg.cache import load_dependencies, save_dependencies

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")
    deps = [
        create_package_identifier(system="npm", name="dep1", version="1.0.0"),
        create_package_identifier(system="npm", name="dep2", version="2.0.0"),
    ]

    save_dependencies(pkg, deps, cache_dir=tmp_path)
    loaded_deps = load_dependencies(pkg, cache_dir=tmp_path)

    assert loaded_deps is not None
    assert len(loaded_deps) == 2
    assert loaded_deps[0].name == "dep1"
    assert loaded_deps[1].name == "dep2"


def test_load_dependencies_returns_none_when_missing(tmp_path: Path) -> None:
    from iceberg.cache import load_dependencies

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")
    loaded_deps = load_dependencies(pkg, cache_dir=tmp_path)

    assert loaded_deps is None


def test_save_discovered_repos_creates_source_directory(tmp_path: Path) -> None:
    from iceberg.cache import save_discovered_repos

    repos = [
        create_discovered_repo(name="repo1", source="trending-daily"),
        create_discovered_repo(name="repo2", source="trending-daily"),
    ]

    save_discovered_repos(repos, cache_dir=tmp_path)

    today = datetime.now(timezone.utc).date().isoformat()
    cache_file = tmp_path / "discovered" / "trending-daily" / f"{today}.json"

    assert cache_file.exists()


def test_save_discovered_repos_with_search_source(tmp_path: Path) -> None:
    from iceberg.cache import save_discovered_repos

    repos = [
        create_discovered_repo(
            name="react",
            source="search",
            search_query="stars:>10000 language:javascript",
        ),
    ]

    save_discovered_repos(repos, cache_dir=tmp_path)

    # Should create a hash-based filename for search queries
    search_dir = tmp_path / "discovered" / "search"
    assert search_dir.exists()

    # Should have created a cache file
    cache_files = list(search_dir.glob("*.json"))
    assert len(cache_files) == 1


def test_load_discovered_repos_by_source_and_date(tmp_path: Path) -> None:
    from iceberg.cache import load_discovered_repos, save_discovered_repos

    repos = [
        create_discovered_repo(name="repo1", source="trending-daily", stars=1000),
        create_discovered_repo(name="repo2", source="trending-daily", stars=2000),
    ]

    save_discovered_repos(repos, cache_dir=tmp_path)

    today = datetime.now(timezone.utc).date().isoformat()
    loaded = load_discovered_repos("trending-daily", today, cache_dir=tmp_path)

    assert loaded is not None
    assert len(loaded) == 2
    assert loaded[0].name == "repo1"
    assert loaded[0].source == "trending-daily"
    assert loaded[1].stars == 2000


def test_load_discovered_repos_with_search_query(tmp_path: Path) -> None:
    from iceberg.cache import load_discovered_repos, save_discovered_repos

    query = "stars:>10000 language:python"
    repos = [
        create_discovered_repo(name="requests", source="search", search_query=query),
    ]

    save_discovered_repos(repos, cache_dir=tmp_path)

    # Load using query hash
    loaded = load_discovered_repos("search", query, cache_dir=tmp_path)

    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0].name == "requests"
    assert loaded[0].search_query == query


def test_load_discovered_repos_returns_none_when_missing(tmp_path: Path) -> None:
    from iceberg.cache import load_discovered_repos

    loaded = load_discovered_repos("trending-daily", "2026-01-01", cache_dir=tmp_path)

    assert loaded is None


def test_discovered_repos_cache_isolation(tmp_path: Path) -> None:
    from iceberg.cache import load_discovered_repos, save_discovered_repos

    # Save to trending-daily
    daily_repos = [create_discovered_repo(name="repo1", source="trending-daily")]
    save_discovered_repos(daily_repos, cache_dir=tmp_path)

    # Save to trending-weekly
    weekly_repos = [create_discovered_repo(name="repo2", source="trending-weekly")]
    save_discovered_repos(weekly_repos, cache_dir=tmp_path)

    # Verify they don't collide
    today = datetime.now(timezone.utc).date().isoformat()
    loaded_daily = load_discovered_repos("trending-daily", today, cache_dir=tmp_path)
    loaded_weekly = load_discovered_repos("trending-weekly", today, cache_dir=tmp_path)

    assert loaded_daily is not None
    assert loaded_weekly is not None
    assert loaded_daily[0].name == "repo1"
    assert loaded_weekly[0].name == "repo2"


def test_backward_compatibility_with_old_trending_cache(tmp_path: Path) -> None:
    from iceberg.cache import load_discovered_repos, save_trending_repos

    # Save using old function
    repos = [create_discovered_repo(name="old-repo", source="trending-daily")]
    save_trending_repos(repos, cache_dir=tmp_path)

    # Load using new function should fall back to old cache
    today = datetime.now(timezone.utc).date().isoformat()
    loaded = load_discovered_repos("trending-daily", today, cache_dir=tmp_path)

    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0].name == "old-repo"
