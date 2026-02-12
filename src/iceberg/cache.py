import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from iceberg.models import DiscoveredRepo, LocMetrics, PackageIdentifier, TrendingRepo


def get_default_cache_dir() -> Path:
    return Path(__file__).parent.parent.parent / "cache"


def save_trending_repos(
    repos: list[TrendingRepo],
    cache_dir: Path | None = None,
) -> None:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    trending_dir = cache_dir / "trending"
    trending_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).date().isoformat()
    cache_file = trending_dir / f"{today}.json"

    data = [repo.model_dump(mode="json") for repo in repos]

    cache_file.write_text(json.dumps(data, indent=2))


def load_trending_repos(
    cache_dir: Path | None = None,
) -> list[TrendingRepo] | None:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    trending_dir = cache_dir / "trending"
    today = datetime.now(timezone.utc).date().isoformat()
    cache_file = trending_dir / f"{today}.json"

    if not cache_file.exists():
        return None

    data = json.loads(cache_file.read_text())
    return [TrendingRepo.model_validate(item) for item in data]


def save_loc_metrics(
    metrics: LocMetrics,
    cache_dir: Path | None = None,
) -> None:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    pkg = metrics.package
    loc_dir = cache_dir / "loc" / pkg.system / pkg.name
    loc_dir.mkdir(parents=True, exist_ok=True)

    cache_file = loc_dir / f"{pkg.version}.json"

    data = metrics.model_dump(mode="json")
    cache_file.write_text(json.dumps(data, indent=2))


def load_loc_metrics(
    pkg: PackageIdentifier,
    cache_dir: Path | None = None,
) -> LocMetrics | None:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    cache_file = cache_dir / "loc" / pkg.system / pkg.name / f"{pkg.version}.json"

    if not cache_file.exists():
        return None

    data = json.loads(cache_file.read_text())
    return LocMetrics.model_validate(data)


def save_dependencies(
    pkg: PackageIdentifier,
    deps: list[PackageIdentifier],
    cache_dir: Path | None = None,
) -> None:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    deps_dir = cache_dir / "dependencies" / pkg.system / pkg.name
    deps_dir.mkdir(parents=True, exist_ok=True)

    cache_file = deps_dir / f"{pkg.version}.json"

    data = [dep.model_dump(mode="json") for dep in deps]
    cache_file.write_text(json.dumps(data, indent=2))


def load_dependencies(
    pkg: PackageIdentifier,
    cache_dir: Path | None = None,
) -> list[PackageIdentifier] | None:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    cache_file = cache_dir / "dependencies" / pkg.system / pkg.name / f"{pkg.version}.json"

    if not cache_file.exists():
        return None

    data = json.loads(cache_file.read_text())
    return [PackageIdentifier.model_validate(item) for item in data]


def is_cache_fresh(
    cache_dir: Path | None = None,
    max_age_days: int = 7,
) -> bool:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    trending_dir = cache_dir / "trending"
    today = datetime.now(timezone.utc).date().isoformat()
    cache_file = trending_dir / f"{today}.json"

    if not cache_file.exists():
        return False

    file_date_str = cache_file.stem
    file_date = datetime.fromisoformat(file_date_str).replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    age = now - file_date
    return age <= timedelta(days=max_age_days)


def save_project_loc(
    project_data: dict[str, Any],
    cache_dir: Path | None = None,
) -> None:
    """Save project LoC data to versioned cache.

    Args:
        project_data: Dict with owner, repo, version, loc, source, etc.
        cache_dir: Cache directory
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    owner = project_data["owner"]
    repo = project_data["repo"]
    version = project_data["version"]

    project_dir = cache_dir / "projects" / owner / repo
    project_dir.mkdir(parents=True, exist_ok=True)

    cache_file = project_dir / f"{version}.json"
    cache_file.write_text(json.dumps(project_data, indent=2))


def load_project_loc(
    owner: str,
    repo: str,
    version: str,
    cache_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Load project LoC data from versioned cache.

    Args:
        owner: Repository owner
        repo: Repository name
        version: Version tag (e.g., v1.0.0)
        cache_dir: Cache directory

    Returns:
        Project data dict or None if not cached
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    cache_file = cache_dir / "projects" / owner / repo / f"{version}.json"

    if not cache_file.exists():
        return None

    data: dict[str, Any] = json.loads(cache_file.read_text())
    return data


def list_project_versions(
    owner: str,
    repo: str,
    cache_dir: Path | None = None,
) -> list[str]:
    """List all cached versions for a project.

    Args:
        owner: Repository owner
        repo: Repository name
        cache_dir: Cache directory

    Returns:
        List of version strings (e.g., ["v1.0.0", "v2.0.0"])
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    project_dir = cache_dir / "projects" / owner / repo

    if not project_dir.exists():
        return []

    versions = []
    for file_path in project_dir.glob("*.json"):
        versions.append(file_path.stem)

    return sorted(versions)


def _hash_query(query: str) -> str:
    """Generate deterministic hash for search query.

    Args:
        query: Search query string

    Returns:
        16-character hex hash of query
    """
    return hashlib.sha256(query.encode()).hexdigest()[:16]


def save_discovered_repos(
    repos: list[DiscoveredRepo],
    cache_dir: Path | None = None,
) -> None:
    """DEPRECATED: Save discovered repos with source tracking.

    This function saves to the old cache/discovered/ structure.
    Use save_repo_metadata() instead, which saves to cache/repos/.

    Kept for backwards compatibility and manual inspection only.

    Args:
        repos: List of discovered repositories
        cache_dir: Optional cache directory path

    Cache structure:
        cache/discovered/{source}/{identifier}.json
        - For trending: identifier is date (2026-02-02)
        - For search: identifier is query hash
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    if not repos:
        return

    # Group repos by source
    source = repos[0].source
    discovered_dir = cache_dir / "discovered" / source
    discovered_dir.mkdir(parents=True, exist_ok=True)

    # Determine cache filename
    if source.startswith("trending"):
        # Use date as identifier for trending
        today = datetime.now(timezone.utc).date().isoformat()
        cache_file = discovered_dir / f"{today}.json"
    elif source == "search":
        # Use query hash as identifier for search
        query = repos[0].search_query or ""
        query_hash = _hash_query(query)
        cache_file = discovered_dir / f"{query_hash}.json"
    else:
        # Fallback: use timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        cache_file = discovered_dir / f"{timestamp}.json"

    data = [repo.model_dump(mode="json") for repo in repos]
    cache_file.write_text(json.dumps(data, indent=2))


def load_discovered_repos(
    source: str,
    identifier: str,
    cache_dir: Path | None = None,
) -> list[DiscoveredRepo] | None:
    """DEPRECATED: Load discovered repos by source and identifier.

    This function loads from the old cache/discovered/ structure.
    Use list_all_repos() or get_repos_by_category() instead.

    Kept for backwards compatibility and manual inspection only.

    Args:
        source: Source type (trending-monthly, search, github-ranking-python)
        identifier: Date for trending (2026-02-02) or query for search
        cache_dir: Optional cache directory path

    Returns:
        List of discovered repos or None if not cached
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    # Determine cache file path
    if source.startswith("trending"):
        cache_file = cache_dir / "discovered" / source / f"{identifier}.json"
    elif source == "search":
        # For search, identifier is the query - hash it
        query_hash = _hash_query(identifier)
        cache_file = cache_dir / "discovered" / "search" / f"{query_hash}.json"
    else:
        cache_file = cache_dir / "discovered" / source / f"{identifier}.json"

    if not cache_file.exists():
        return None

    data = json.loads(cache_file.read_text())
    return [DiscoveredRepo.model_validate(item) for item in data]


# ============================================================================
# Repo Metadata Functions (Discovery Info with Categories)
# ============================================================================

def save_repo_metadata(
    repo: DiscoveredRepo,
    category: str,
    cache_dir: Path | None = None,
) -> None:
    """Save or update repository discovery metadata.

    Tracks which categories a repo was discovered in. A repo can be in multiple
    categories (e.g., Top-100-stars AND Python AND monthly trending).

    Args:
        repo: Discovered repository
        category: Category it was found in (e.g., "github-ranking-python", "trending-monthly")
        cache_dir: Optional cache directory

    Cache structure:
        cache/repos/{owner}/{repo}.json
        {
            "owner": "...",
            "name": "...",
            "url": "...",
            "description": "...",
            "language": "...",
            "stars": 12345,
            "categories": {
                "github-ranking-python": "2026-02-09",
                "trending-monthly": "2026-02-09"
            },
            "last_discovered": "2026-02-09"
        }
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    repo_dir = cache_dir / "repos" / repo.owner
    repo_dir.mkdir(parents=True, exist_ok=True)

    repo_file = repo_dir / f"{repo.name}.json"

    today = datetime.now(timezone.utc).date().isoformat()

    # Load existing metadata if present
    if repo_file.exists():
        existing_data = json.loads(repo_file.read_text())
        categories = existing_data.get("categories", {})
    else:
        categories = {}

    # Update category with discovery date
    categories[category] = today

    # Build metadata
    metadata = {
        "owner": repo.owner,
        "name": repo.name,
        "url": str(repo.url),
        "description": repo.description,
        "language": repo.language,
        "stars": repo.stars,
        "categories": categories,
        "last_discovered": today,
    }

    repo_file.write_text(json.dumps(metadata, indent=2))


def load_repo_metadata(
    owner: str,
    name: str,
    cache_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Load repository discovery metadata.

    Args:
        owner: Repository owner
        name: Repository name
        cache_dir: Optional cache directory

    Returns:
        Repository metadata dict or None if not found
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    repo_file = cache_dir / "repos" / owner / f"{name}.json"

    if not repo_file.exists():
        return None

    return json.loads(repo_file.read_text())


def list_all_repos(
    cache_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """List all discovered repositories.

    Args:
        cache_dir: Optional cache directory

    Returns:
        List of repository metadata dicts
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    repos_dir = cache_dir / "repos"

    if not repos_dir.exists():
        return []

    all_repos = []
    for owner_dir in repos_dir.iterdir():
        if not owner_dir.is_dir():
            continue

        for repo_file in owner_dir.glob("*.json"):
            metadata = json.loads(repo_file.read_text())
            all_repos.append(metadata)

    return all_repos


def get_repos_by_category(
    category: str,
    cache_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Get all repos that were discovered in a specific category.

    Args:
        category: Category to filter by (e.g., "github-ranking-python")
        cache_dir: Optional cache directory

    Returns:
        List of repository metadata dicts
    """
    all_repos = list_all_repos(cache_dir=cache_dir)
    return [
        repo for repo in all_repos
        if category in repo.get("categories", {})
    ]
