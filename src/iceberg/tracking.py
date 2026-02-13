"""Repository tracking for continuous updates.

Tracking is stored as a 'tracked' category in repo metadata
(cache/repos/{owner}/{repo}.json), just like discovery sources.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iceberg.cache import get_default_cache_dir, load_project_loc, load_repo_metadata
from iceberg.github_loc import get_current_head_hash

logger = logging.getLogger(__name__)


def _save_repo_metadata(owner: str, repo: str, cache_dir: Path, data: dict[str, Any]) -> None:
    path = cache_dir / "repos" / owner / f"{repo}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def load_tracked_repos(cache_dir: Path | None = None) -> list[dict[str, str]]:
    """Load list of tracked repositories.

    Scans all repo metadata files for repos with 'tracked' in categories.

    Returns:
        List of dicts with 'owner', 'repo', and 'added_at' keys
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    repos_dir = cache_dir / "repos"
    if not repos_dir.exists():
        return []

    tracked = []
    for owner_dir in repos_dir.iterdir():
        if not owner_dir.is_dir():
            continue
        for repo_file in owner_dir.iterdir():
            if not repo_file.name.endswith(".json"):
                continue
            try:
                data = json.loads(repo_file.read_text())
                categories = data.get("categories", {})
                if "tracked" in categories:
                    tracked.append({
                        "owner": data.get("owner", owner_dir.name),
                        "repo": data.get("name", repo_file.stem),
                        "added_at": categories["tracked"],
                    })
            except (json.JSONDecodeError, IOError) as e:
                logger.debug(f"Failed to load tracked repo from {repo_file}: {e}")
                continue

    return tracked


def save_tracked_repo(owner: str, repo: str, cache_dir: Path | None = None) -> None:
    """Add a repository to tracking by adding 'tracked' to its categories."""
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    today = datetime.now(timezone.utc).date().isoformat()
    data = load_repo_metadata(owner, repo, cache_dir)

    if data is None:
        data = {
            "owner": owner,
            "name": repo,
            "categories": {},
        }

    categories = data.get("categories", {})
    if "tracked" in categories:
        logger.debug(f"{owner}/{repo} is already tracked")
        return

    categories["tracked"] = today
    data["categories"] = categories
    _save_repo_metadata(owner, repo, cache_dir, data)
    logger.info(f"Added {owner}/{repo} to tracking")


def remove_tracked_repo(owner: str, repo: str, cache_dir: Path | None = None) -> None:
    """Remove a repository from tracking by removing 'tracked' from its categories."""
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    data = load_repo_metadata(owner, repo, cache_dir)
    if data is None:
        logger.debug(f"{owner}/{repo} not found in metadata")
        return

    categories = data.get("categories", {})
    if "tracked" not in categories:
        logger.debug(f"{owner}/{repo} is not tracked")
        return

    del categories["tracked"]
    data["categories"] = categories
    _save_repo_metadata(owner, repo, cache_dir, data)
    logger.info(f"Removed {owner}/{repo} from tracking")


def is_repo_tracked(owner: str, repo: str, cache_dir: Path | None = None) -> bool:
    """Check if a repository is being tracked."""
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    data = load_repo_metadata(owner, repo, cache_dir)
    if data is None:
        return False

    return "tracked" in data.get("categories", {})


def needs_update(owner: str, repo: str, cache_dir: Path | None = None) -> tuple[bool, str | None]:
    """Check if a cached repository needs updating.

    Compares the cached commit hash with the current HEAD.

    Args:
        owner: Repository owner
        repo: Repository name
        cache_dir: Cache directory

    Returns:
        Tuple of (needs_update: bool, reason: str | None)
    """
    # Check if we have any cached version
    cached = load_project_loc(owner, repo, "HEAD", cache_dir=cache_dir)

    if not cached:
        return (True, "not cached")

    # Get cached commit hash
    cached_hash = cached.get("commit_hash")
    if not cached_hash:
        return (True, "no commit hash in cache")

    # Get current HEAD hash
    current_hash = get_current_head_hash(owner, repo)
    if not current_hash:
        return (False, "could not fetch current HEAD")

    # Compare hashes
    if cached_hash[:8] != current_hash[:8]:  # Compare first 8 chars (short hash)
        return (True, f"new commits (cached: {cached_hash[:8]}, current: {current_hash})")

    return (False, "up to date")
