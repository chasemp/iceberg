"""Repository tracking for continuous updates."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iceberg.cache import get_default_cache_dir, load_project_loc
from iceberg.github_loc import get_current_head_hash


def get_tracked_file(cache_dir: Path | None = None) -> Path:
    """Get path to tracked repositories file."""
    if cache_dir is None:
        cache_dir = get_default_cache_dir()
    return cache_dir / "tracked.json"


def load_tracked_repos(cache_dir: Path | None = None) -> list[dict[str, str]]:
    """Load list of tracked repositories.
    
    Returns:
        List of dicts with 'owner' and 'repo' keys
    """
    tracked_file = get_tracked_file(cache_dir)
    
    if not tracked_file.exists():
        return []
    
    data: dict[str, Any] = json.loads(tracked_file.read_text())
    return data.get("repositories", [])


def save_tracked_repos(repos: list[dict[str, str]], cache_dir: Path | None = None) -> None:
    """Save list of tracked repositories."""
    tracked_file = get_tracked_file(cache_dir)
    tracked_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "repositories": repos,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    tracked_file.write_text(json.dumps(data, indent=2))


def save_tracked_repo(owner: str, repo: str, cache_dir: Path | None = None) -> None:
    """Add a repository to tracking list."""
    repos = load_tracked_repos(cache_dir)
    
    # Check if already tracked
    if any(r["owner"] == owner and r["repo"] == repo for r in repos):
        return
    
    repos.append({
        "owner": owner,
        "repo": repo,
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    
    save_tracked_repos(repos, cache_dir)


def remove_tracked_repo(owner: str, repo: str, cache_dir: Path | None = None) -> None:
    """Remove a repository from tracking list."""
    repos = load_tracked_repos(cache_dir)
    repos = [r for r in repos if not (r["owner"] == owner and r["repo"] == repo)]
    save_tracked_repos(repos, cache_dir)


def is_repo_tracked(owner: str, repo: str, cache_dir: Path | None = None) -> bool:
    """Check if a repository is being tracked."""
    repos = load_tracked_repos(cache_dir)
    return any(r["owner"] == owner and r["repo"] == repo for r in repos)


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
