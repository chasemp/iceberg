import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "staleness.json"

_TIER_PRIORITY = {"tracked": 0, "popular": 1, "regular": 2}


def load_staleness_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or _DEFAULT_CONFIG_PATH
    return json.loads(path.read_text())


def determine_tier(
    owner: str,
    repo: str,
    cache_dir: Path,
    config: dict[str, Any],
) -> str:
    from iceberg.cache import load_repo_metadata
    from iceberg.tracking import is_repo_tracked

    if is_repo_tracked(owner, repo, cache_dir=cache_dir):
        return "tracked"

    repo_meta = load_repo_metadata(owner, repo, cache_dir)
    stars = repo_meta.get("stars", 0) if repo_meta else 0
    threshold = config["tiers"]["popular"].get("stars_threshold", 10000)

    if stars >= threshold:
        return "popular"

    return "regular"


def is_stale(
    owner: str,
    repo: str,
    cache_dir: Path,
    config: dict[str, Any],
    force: bool = False,
) -> tuple[bool, str]:
    from iceberg.cache import load_project_loc

    cached = load_project_loc(owner, repo, "HEAD", cache_dir=cache_dir)

    if not cached:
        logger.debug(f"{owner}/{repo}: no analysis data (stale)")
        return (True, "no analysis data")

    if force:
        return (True, "forced re-analysis")

    cached_at = cached.get("cached_at")
    if not cached_at:
        return (True, "no cached_at timestamp")

    age = _calculate_age(cached_at)
    age_hours = age.total_seconds() / 3600

    min_age_hours = config.get("min_age_hours", 1)
    if age_hours < min_age_hours:
        return (False, f"analyzed {age_hours:.1f}h ago")

    tier = determine_tier(owner, repo, cache_dir, config)
    tiers = config["tiers"]

    if tier == "tracked":
        max_hours = tiers["tracked"].get("max_age_hours", 24)
        if age_hours > max_hours:
            return (True, f"tracked, {age_hours / 24:.1f} days old")
    elif tier == "popular":
        max_days = tiers["popular"].get("max_age_days", 7)
        if age_hours > max_days * 24:
            return (True, f"popular, {age_hours / 24:.1f} days old")
    else:
        max_days = tiers["regular"].get("max_age_days", 30)
        if age_hours > max_days * 24:
            return (True, f"regular, {age_hours / 24:.1f} days old")

    return (False, f"up to date ({age_hours / 24:.1f} days old)")


def prioritize_repos(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(repos, key=lambda r: _TIER_PRIORITY.get(r.get("tier", "regular"), 2))


def _calculate_age(cached_at: str) -> timedelta:
    try:
        cached_time = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - cached_time
    except Exception as e:
        logger.debug(f"Failed to parse cached_at timestamp '{cached_at}': {e}")
        return timedelta(days=999)
