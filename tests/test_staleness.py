import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def _make_config() -> dict:
    return {
        "tiers": {
            "tracked": {"max_age_hours": 24},
            "popular": {"stars_threshold": 10000, "max_age_days": 7},
            "regular": {"max_age_days": 30},
        },
        "min_age_hours": 1,
        "batch_pause_every_n": 10,
        "batch_pause_seconds": 2,
        "default_batch_size": 25,
    }


def _make_cached_analysis(
    owner: str = "test",
    repo: str = "repo",
    hours_ago: float = 48,
    loc: int = 5000,
) -> dict:
    cached_at = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    return {
        "owner": owner,
        "repo": repo,
        "version": "HEAD",
        "loc": loc,
        "source": "github_clone",
        "cached_at": cached_at,
    }


def _write_analysis(tmp_path: Path, owner: str, repo: str, data: dict) -> None:
    project_dir = tmp_path / "projects" / owner / repo
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "HEAD.json").write_text(json.dumps(data))


def _write_repo_metadata(
    tmp_path: Path, owner: str, repo: str, stars: int = 100,
    categories: dict | None = None,
) -> None:
    repos_dir = tmp_path / "repos" / owner
    repos_dir.mkdir(parents=True, exist_ok=True)
    data = {"owner": owner, "name": repo, "stars": stars}
    if categories:
        data["categories"] = categories
    (repos_dir / f"{repo}.json").write_text(json.dumps(data))


def test_load_staleness_config_reads_json(tmp_path: Path) -> None:
    from iceberg.staleness import load_staleness_config

    config = _make_config()
    config_path = tmp_path / "staleness.json"
    config_path.write_text(json.dumps(config))

    result = load_staleness_config(config_path)

    assert result["tiers"]["tracked"]["max_age_hours"] == 24
    assert result["default_batch_size"] == 25


def test_load_staleness_config_uses_default_path() -> None:
    from iceberg.staleness import load_staleness_config

    result = load_staleness_config()

    assert "tiers" in result
    assert "tracked" in result["tiers"]


def test_is_stale_returns_true_for_missing_analysis(tmp_path: Path) -> None:
    from iceberg.staleness import is_stale

    config = _make_config()
    _write_repo_metadata(tmp_path, "test", "repo", stars=100)

    stale, reason = is_stale("test", "repo", cache_dir=tmp_path, config=config)

    assert stale is True
    assert "no analysis" in reason


def test_is_stale_returns_true_for_tracked_repo_past_threshold(
    tmp_path: Path,
) -> None:
    from iceberg.staleness import is_stale

    config = _make_config()
    analysis = _make_cached_analysis(hours_ago=48)
    _write_analysis(tmp_path, "test", "repo", analysis)
    _write_repo_metadata(
        tmp_path, "test", "repo", categories={"tracked": "2025-01-01"}
    )

    stale, reason = is_stale("test", "repo", cache_dir=tmp_path, config=config)

    assert stale is True
    assert "tracked" in reason


def test_is_stale_returns_false_for_tracked_repo_within_threshold(
    tmp_path: Path,
) -> None:
    from iceberg.staleness import is_stale

    config = _make_config()
    analysis = _make_cached_analysis(hours_ago=0.5)
    _write_analysis(tmp_path, "test", "repo", analysis)
    _write_repo_metadata(
        tmp_path, "test", "repo", categories={"tracked": "2025-01-01"}
    )

    stale, reason = is_stale("test", "repo", cache_dir=tmp_path, config=config)

    assert stale is False


def test_is_stale_returns_true_for_popular_repo_past_threshold(
    tmp_path: Path,
) -> None:
    from iceberg.staleness import is_stale

    config = _make_config()
    analysis = _make_cached_analysis(hours_ago=8 * 24)
    _write_analysis(tmp_path, "test", "repo", analysis)
    _write_repo_metadata(tmp_path, "test", "repo", stars=50000)

    stale, reason = is_stale("test", "repo", cache_dir=tmp_path, config=config)

    assert stale is True
    assert "popular" in reason


def test_is_stale_returns_false_for_popular_repo_within_threshold(
    tmp_path: Path,
) -> None:
    from iceberg.staleness import is_stale

    config = _make_config()
    analysis = _make_cached_analysis(hours_ago=3 * 24)
    _write_analysis(tmp_path, "test", "repo", analysis)
    _write_repo_metadata(tmp_path, "test", "repo", stars=50000)

    stale, reason = is_stale("test", "repo", cache_dir=tmp_path, config=config)

    assert stale is False


def test_is_stale_returns_true_for_regular_repo_past_threshold(
    tmp_path: Path,
) -> None:
    from iceberg.staleness import is_stale

    config = _make_config()
    analysis = _make_cached_analysis(hours_ago=35 * 24)
    _write_analysis(tmp_path, "test", "repo", analysis)
    _write_repo_metadata(tmp_path, "test", "repo", stars=500)

    stale, reason = is_stale("test", "repo", cache_dir=tmp_path, config=config)

    assert stale is True
    assert "regular" in reason


def test_is_stale_returns_false_for_regular_repo_within_threshold(
    tmp_path: Path,
) -> None:
    from iceberg.staleness import is_stale

    config = _make_config()
    analysis = _make_cached_analysis(hours_ago=10 * 24)
    _write_analysis(tmp_path, "test", "repo", analysis)
    _write_repo_metadata(tmp_path, "test", "repo", stars=500)

    stale, reason = is_stale("test", "repo", cache_dir=tmp_path, config=config)

    assert stale is False


def test_is_stale_returns_true_when_force_is_set(tmp_path: Path) -> None:
    from iceberg.staleness import is_stale

    config = _make_config()
    analysis = _make_cached_analysis(hours_ago=0.5)
    _write_analysis(tmp_path, "test", "repo", analysis)
    _write_repo_metadata(tmp_path, "test", "repo", stars=500)

    stale, reason = is_stale(
        "test", "repo", cache_dir=tmp_path, config=config, force=True
    )

    assert stale is True
    assert "forced" in reason


def test_is_stale_skips_very_recent_even_when_tracked(tmp_path: Path) -> None:
    """Repos analyzed less than min_age_hours ago are skipped even if tracked."""
    from iceberg.staleness import is_stale

    config = _make_config()
    config["min_age_hours"] = 1
    analysis = _make_cached_analysis(hours_ago=0.25)
    _write_analysis(tmp_path, "test", "repo", analysis)
    _write_repo_metadata(
        tmp_path, "test", "repo", categories={"tracked": "2025-01-01"}
    )

    stale, reason = is_stale("test", "repo", cache_dir=tmp_path, config=config)

    assert stale is False
    assert "recent" in reason.lower() or "ago" in reason.lower()


def test_determine_tier_tracked(tmp_path: Path) -> None:
    from iceberg.staleness import determine_tier

    config = _make_config()
    _write_repo_metadata(
        tmp_path, "test", "repo", categories={"tracked": "2025-01-01"}
    )

    tier = determine_tier("test", "repo", cache_dir=tmp_path, config=config)
    assert tier == "tracked"


def test_determine_tier_popular(tmp_path: Path) -> None:
    from iceberg.staleness import determine_tier

    config = _make_config()
    _write_repo_metadata(tmp_path, "test", "repo", stars=50000)

    tier = determine_tier("test", "repo", cache_dir=tmp_path, config=config)
    assert tier == "popular"


def test_determine_tier_regular(tmp_path: Path) -> None:
    from iceberg.staleness import determine_tier

    config = _make_config()
    _write_repo_metadata(tmp_path, "test", "repo", stars=500)

    tier = determine_tier("test", "repo", cache_dir=tmp_path, config=config)
    assert tier == "regular"


def test_prioritize_repos_orders_by_tier() -> None:
    from iceberg.staleness import prioritize_repos

    repos = [
        {"owner": "a", "name": "regular", "tier": "regular"},
        {"owner": "b", "name": "tracked", "tier": "tracked"},
        {"owner": "c", "name": "popular", "tier": "popular"},
    ]

    result = prioritize_repos(repos)

    assert result[0]["tier"] == "tracked"
    assert result[1]["tier"] == "popular"
    assert result[2]["tier"] == "regular"
