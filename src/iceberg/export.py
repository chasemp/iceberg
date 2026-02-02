"""Export cached data to SPA-friendly JSON format.

This module transforms the internal cache structure into JSON files
optimized for the GitHub Pages SPA, enabling:
- Discovery browsing by dimension/timeframe
- Repository detail pages with visualizations
- Dependency graph exploration
- Dependency rankings and statistics
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iceberg.cache import get_default_cache_dir, load_discovered_repos, load_project_loc
from iceberg.models import DiscoveredRepo


def export_discovery_index(
    output_dir: Path,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Export index of all discovery dimensions and their repositories.

    Creates a structured index showing what repos were discovered through
    each dimension (trending-daily, trending-weekly, search queries, etc.)

    Args:
        output_dir: Directory to write JSON files
        cache_dir: Optional cache directory to read from

    Returns:
        Dictionary summarizing what was exported

    Output structure:
        {
          "dimensions": [
            {
              "id": "trending-daily",
              "type": "trending",
              "timeframe": "daily",
              "snapshots": [
                {
                  "date": "2026-02-02",
                  "count": 25,
                  "repos": [...]
                }
              ]
            },
            {
              "id": "search:stars>10000",
              "type": "search",
              "query": "stars:>10000",
              "count": 50,
              "repos": [...]
            }
          ],
          "generated_at": "2026-02-02T12:00:00Z"
        }
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    discovered_dir = cache_dir / "discovered"
    if not discovered_dir.exists():
        index = {
            "dimensions": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "index.json"
        output_file.write_text(json.dumps(index, indent=2))
        return {"dimensions_exported": 0, "output_file": str(output_file)}

    dimensions: list[dict[str, Any]] = []

    # Scan all source directories
    for source_dir in discovered_dir.iterdir():
        if not source_dir.is_dir():
            continue

        source = source_dir.name

        if source.startswith("trending"):
            # Trending dimensions: one snapshot per date
            snapshots = []
            for cache_file in sorted(source_dir.glob("*.json")):
                date = cache_file.stem
                repos = load_discovered_repos(source, date, cache_dir=cache_dir)
                if repos:
                    snapshots.append({
                        "date": date,
                        "count": len(repos),
                        "repos": [_repo_summary(repo) for repo in repos],
                    })

            if snapshots:
                dimensions.append({
                    "id": source,
                    "type": "trending",
                    "timeframe": source.replace("trending-", ""),
                    "snapshots": snapshots,
                })

        elif source == "search":
            # Search dimensions: one entry per query hash
            for cache_file in source_dir.glob("*.json"):
                data = json.loads(cache_file.read_text())
                if data:
                    repos = [DiscoveredRepo.model_validate(item) for item in data]
                    query = repos[0].search_query if repos else "unknown"

                    dimensions.append({
                        "id": f"search:{query}",
                        "type": "search",
                        "query": query,
                        "count": len(repos),
                        "repos": [_repo_summary(repo) for repo in repos],
                    })

    index = {
        "dimensions": dimensions,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Write to output
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "index.json"
    output_file.write_text(json.dumps(index, indent=2))

    return {
        "dimensions_exported": len(dimensions),
        "output_file": str(output_file),
    }


def _repo_summary(repo: DiscoveredRepo) -> dict[str, Any]:
    """Create a summary dict of a repo for index files."""
    return {
        "owner": repo.owner,
        "name": repo.name,
        "full_name": f"{repo.owner}/{repo.name}",
        "url": str(repo.url),
        "description": repo.description,
        "language": repo.language,
        "stars": repo.stars,
        "discovered_at": repo.discovered_at,
    }


def export_repository_details(
    output_dir: Path,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Export detailed analysis data for each analyzed repository.

    Creates individual JSON files for each repository containing:
    - Project LoC
    - Package LoC and dependencies
    - Iceberg ratio
    - Analysis metadata

    Args:
        output_dir: Directory to write JSON files
        cache_dir: Optional cache directory to read from

    Returns:
        Dictionary summarizing what was exported
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    projects_dir = cache_dir / "projects"
    if not projects_dir.exists():
        return {"repos_exported": 0}

    repos_dir = output_dir / "repos"
    repos_dir.mkdir(parents=True, exist_ok=True)

    exported_count = 0

    # Iterate through all analyzed projects
    for owner_dir in projects_dir.iterdir():
        if not owner_dir.is_dir():
            continue

        for repo_dir in owner_dir.iterdir():
            if not repo_dir.is_dir():
                continue

            owner = owner_dir.name
            repo = repo_dir.name

            # Find latest analysis (prefer HEAD, then latest version)
            head_file = repo_dir / "HEAD.json"
            if head_file.exists():
                analysis = json.loads(head_file.read_text())
            else:
                # Get latest version file
                version_files = sorted(repo_dir.glob("*.json"), reverse=True)
                if not version_files:
                    continue
                analysis = json.loads(version_files[0].read_text())

            # Export repo details
            repo_data = {
                "owner": owner,
                "repo": repo,
                "full_name": f"{owner}/{repo}",
                "url": f"https://github.com/{owner}/{repo}",
                "analysis": analysis,
            }

            output_file = repos_dir / f"{owner}-{repo}.json"
            output_file.write_text(json.dumps(repo_data, indent=2))
            exported_count += 1

    return {
        "repos_exported": exported_count,
        "output_dir": str(repos_dir),
    }


def export_all(
    output_dir: Path,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Export all data for SPA consumption.

    Convenience function that runs all export functions.

    Args:
        output_dir: Directory to write all JSON files
        cache_dir: Optional cache directory to read from

    Returns:
        Combined summary of all exports
    """
    results = {}

    results["discovery_index"] = export_discovery_index(output_dir, cache_dir)
    results["repository_details"] = export_repository_details(output_dir, cache_dir)

    return results
