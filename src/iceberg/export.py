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

from iceberg.cache import (
    get_default_cache_dir,
    get_repos_by_category,
    list_all_repos,
    load_dependencies,
    load_discovered_repos,
    load_project_loc,
)
from iceberg.models import DiscoveredRepo, PackageIdentifier


def export_discovery_index(
    output_dir: Path,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Export index of all discovery dimensions and their repositories.

    Creates a structured index showing what repos were discovered through
    each category (trending-weekly, github-ranking-python, etc.)

    Args:
        output_dir: Directory to write JSON files
        cache_dir: Optional cache directory to read from

    Returns:
        Dictionary summarizing what was exported

    Output structure:
        {
          "dimensions": [
            {
              "id": "trending-monthly",
              "type": "trending",
              "timeframe": "monthly",
              "count": 25,
              "repos": [...]
            },
            {
              "id": "github-ranking-python",
              "type": "github-ranking",
              "category": "python",
              "count": 50,
              "repos": [...]
            }
          ],
          "generated_at": "2026-02-09T12:00:00Z"
        }
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    repos_dir = cache_dir / "repos"

    dimensions: list[dict[str, Any]] = []

    if not repos_dir.exists():
        index: dict[str, Any] = {
            "dimensions": dimensions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "index.json"
        output_file.write_text(json.dumps(index, indent=2))
        return {"dimensions_exported": 0, "output_file": str(output_file)}

    # Get all repos and extract unique categories
    all_repos = list_all_repos(cache_dir=cache_dir)

    # Collect all unique categories
    all_categories: set[str] = set()
    for repo in all_repos:
        all_categories.update(repo.get("categories", {}).keys())

    # Create a dimension for each category
    for category in sorted(all_categories):
        # Get repos in this category
        category_repos = [
            repo for repo in all_repos
            if category in repo.get("categories", {})
        ]

        # Build repo summaries with analysis data
        repo_summaries = [
            summary for repo in category_repos
            if (summary := _repo_summary_from_metadata(repo, cache_dir)) is not None
        ]

        if not repo_summaries:
            continue

        # Determine dimension type and metadata
        dimension: dict[str, Any] = {
            "id": category,
            "count": len(repo_summaries),
            "repos": repo_summaries,
        }

        if category.startswith("trending-"):
            dimension["type"] = "trending"
            dimension["timeframe"] = category.replace("trending-", "")
        elif category.startswith("github-ranking-"):
            dimension["type"] = "github-ranking"
            dimension["category"] = category.replace("github-ranking-", "")
        elif category == "search":
            dimension["type"] = "search"
        else:
            dimension["type"] = "other"

        dimensions.append(dimension)

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


def _repo_summary(repo: DiscoveredRepo, cache_dir: Path) -> dict[str, Any] | None:
    """Create a summary dict of a repo for index files.

    Returns None if the repo has zero LoC (no actual code), so it can be filtered out.
    """
    # Check if repo has actual code (LoC > 0)
    projects_dir = cache_dir / "projects" / repo.owner / repo.name
    if projects_dir.exists():
        head_file = projects_dir / "HEAD.json"
        if head_file.exists():
            try:
                analysis = json.loads(head_file.read_text())
                loc = analysis.get("loc", 0)
                # Skip repos with zero LoC (documentation repos, awesome lists, etc.)
                if loc == 0:
                    return None
            except (json.JSONDecodeError, IOError):
                pass  # If we can't read it, include the repo anyway

    summary: dict[str, Any] = {
        "owner": repo.owner,
        "name": repo.name,
        "full_name": f"{repo.owner}/{repo.name}",
        "url": str(repo.url),
        "description": repo.description,
        "language": repo.language,
        "stars": repo.stars,
        "discovered_at": repo.discovered_at,
    }

    # Try to add analysis data for sorting
    if projects_dir.exists():
        head_file = projects_dir / "HEAD.json"
        if head_file.exists():
            try:
                analysis = json.loads(head_file.read_text())

                # Add AI tools info
                if "ai_tools" in analysis and analysis["ai_tools"]:
                    summary["ai_tools"] = analysis["ai_tools"]

                # Add analysis metrics for sorting
                if "loc" in analysis:
                    summary["project_loc"] = analysis["loc"]
                if "total_loc" in analysis:
                    summary["dep_loc"] = analysis["total_loc"]
                if "ratio" in analysis:
                    summary["ratio"] = analysis["ratio"]
                if "dependencies" in analysis and isinstance(analysis["dependencies"], dict):
                    summary["dep_count"] = len(analysis["dependencies"])

            except (json.JSONDecodeError, IOError):
                pass  # If we can't read it, just skip

    return summary


def _repo_summary_from_metadata(repo_metadata: dict[str, Any], cache_dir: Path) -> dict[str, Any] | None:
    """Create a summary dict from repo metadata (new cache structure).

    Returns None if the repo has zero LoC (no actual code), so it can be filtered out.

    Args:
        repo_metadata: Repository metadata dict from cache/repos/
        cache_dir: Cache directory path
    """
    owner = repo_metadata["owner"]
    name = repo_metadata["name"]

    # Check if repo has actual code (LoC > 0)
    projects_dir = cache_dir / "projects" / owner / name
    if projects_dir.exists():
        head_file = projects_dir / "HEAD.json"
        if head_file.exists():
            try:
                analysis = json.loads(head_file.read_text())
                loc = analysis.get("loc", 0)
                # Skip repos with zero LoC (documentation repos, awesome lists, etc.)
                if loc == 0:
                    return None
            except (json.JSONDecodeError, IOError):
                pass  # If we can't read it, include the repo anyway

    summary: dict[str, Any] = {
        "owner": owner,
        "name": name,
        "full_name": f"{owner}/{name}",
        "url": repo_metadata["url"],
        "description": repo_metadata["description"],
        "language": repo_metadata["language"],
        "stars": repo_metadata["stars"],
        "discovered_at": repo_metadata["last_discovered"],
        "categories": list(repo_metadata.get("categories", {}).keys()),
    }

    # Try to add analysis data for sorting
    if projects_dir.exists():
        head_file = projects_dir / "HEAD.json"
        if head_file.exists():
            try:
                analysis = json.loads(head_file.read_text())

                # Add AI tools info
                if "ai_tools" in analysis and analysis["ai_tools"]:
                    summary["ai_tools"] = analysis["ai_tools"]

                # Add analysis metrics for sorting
                if "loc" in analysis:
                    summary["project_loc"] = analysis["loc"]
                if "total_loc" in analysis:
                    summary["dep_loc"] = analysis["total_loc"]
                if "ratio" in analysis:
                    summary["ratio"] = analysis["ratio"]
                if "dependencies" in analysis and isinstance(analysis["dependencies"], dict):
                    summary["dep_count"] = len(analysis["dependencies"])

            except (json.JSONDecodeError, IOError):
                pass  # If we can't read it, just skip

    return summary


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


def export_dependency_graphs(
    output_dir: Path,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Export dependency graphs for each analyzed repository.

    Creates graph data structures showing dependency relationships.

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
        return {"graphs_exported": 0}

    graphs_dir = output_dir / "graphs"
    graphs_dir.mkdir(parents=True, exist_ok=True)

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

            # Find latest analysis
            head_file = repo_dir / "HEAD.json"
            if head_file.exists():
                analysis = json.loads(head_file.read_text())
            else:
                version_files = sorted(repo_dir.glob("*.json"), reverse=True)
                if not version_files:
                    continue
                analysis = json.loads(version_files[0].read_text())

            # Extract package identifier
            if "package" not in analysis:
                continue

            pkg_data = analysis["package"]
            if isinstance(pkg_data, dict):
                root_pkg = PackageIdentifier.model_validate(pkg_data)
            else:
                continue

            # Build dependency graph using BFS
            nodes: list[dict[str, Any]] = []
            edges: list[dict[str, Any]] = []
            visited: set[str] = set()
            queue: list[PackageIdentifier] = [root_pkg]

            while queue:
                pkg = queue.pop(0)
                pkg_key = f"{pkg.system}:{pkg.name}:{pkg.version}"

                if pkg_key in visited:
                    continue

                visited.add(pkg_key)

                # Add node
                nodes.append({
                    "id": pkg_key,
                    "system": pkg.system,
                    "name": pkg.name,
                    "version": pkg.version,
                })

                # Load dependencies
                deps = load_dependencies(pkg, cache_dir=cache_dir)
                if deps:
                    for dep in deps:
                        dep_key = f"{dep.system}:{dep.name}:{dep.version}"

                        # Add edge
                        edges.append({
                            "from": pkg_key,
                            "to": dep_key,
                        })

                        # Add to queue if not visited
                        if dep_key not in visited:
                            queue.append(dep)

            # Create graph data
            graph_data = {
                "owner": owner,
                "repo": repo,
                "full_name": f"{owner}/{repo}",
                "root_package": f"{root_pkg.system}:{root_pkg.name}:{root_pkg.version}",
                "nodes": nodes,
                "edges": edges,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Write graph file
            output_file = graphs_dir / f"{owner}-{repo}.json"
            output_file.write_text(json.dumps(graph_data, indent=2))
            exported_count += 1

    return {
        "graphs_exported": exported_count,
        "output_dir": str(graphs_dir),
    }


def export_dependency_rankings(
    output_dir: Path,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Export dependency popularity rankings.

    Analyzes all analyzed projects to find which dependencies are most commonly used.

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
        return {"packages_exported": 0}

    # Count package usage across all projects
    package_usage: dict[tuple[str, str], int] = defaultdict(int)

    # Iterate through all analyzed projects
    for owner_dir in projects_dir.iterdir():
        if not owner_dir.is_dir():
            continue

        for repo_dir in owner_dir.iterdir():
            if not repo_dir.is_dir():
                continue

            # Find latest analysis
            head_file = repo_dir / "HEAD.json"
            if head_file.exists():
                analysis = json.loads(head_file.read_text())
            else:
                version_files = sorted(repo_dir.glob("*.json"), reverse=True)
                if not version_files:
                    continue
                analysis = json.loads(version_files[0].read_text())

            # Extract package identifier
            if "package" not in analysis:
                continue

            pkg_data = analysis["package"]
            if isinstance(pkg_data, dict):
                pkg = PackageIdentifier.model_validate(pkg_data)
            else:
                # Skip if package format is unexpected
                continue

            # Load dependencies for this package
            deps = load_dependencies(pkg, cache_dir=cache_dir)
            if not deps:
                continue

            # Count each dependency
            for dep in deps:
                key = (dep.system, dep.name)
                package_usage[key] += 1

    # Sort by usage count (descending)
    sorted_packages = sorted(
        package_usage.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    # Create rankings data
    rankings = {
        "packages": [
            {
                "system": system,
                "name": name,
                "count": count,
            }
            for (system, name), count in sorted_packages
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Write to output
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "rankings.json"
    output_file.write_text(json.dumps(rankings, indent=2))

    return {
        "packages_exported": len(sorted_packages),
        "output_file": str(output_file),
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
    results["dependency_graphs"] = export_dependency_graphs(output_dir, cache_dir)
    results["dependency_rankings"] = export_dependency_rankings(output_dir, cache_dir)

    return results
