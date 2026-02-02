#!/usr/bin/env python3
"""Analyze all discovered repositories from cache.

This script iterates through all repos discovered via trending and search,
detects their primary package, and runs analysis to calculate the iceberg ratio.

Designed to be run by GitHub Actions after fetching new repos.

Usage:
    python analyze_all_discovered.py           # Quiet mode
    python analyze_all_discovered.py -v        # Verbose mode (shows fallbacks)
    python analyze_all_discovered.py --verbose # Verbose mode (shows fallbacks)
"""

import sys
from pathlib import Path

from iceberg.cache import get_default_cache_dir, load_discovered_repos
from iceberg.calculator import analyze_repository
from iceberg.models import DiscoveredRepo


def get_all_discovered_repos(cache_dir: Path | None = None) -> list[DiscoveredRepo]:
    """Load all discovered repos from all sources."""
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    discovered_dir = cache_dir / "discovered"
    if not discovered_dir.exists():
        return []

    all_repos: list[DiscoveredRepo] = []
    seen_repos: set[str] = set()

    # Iterate through all source directories
    for source_dir in discovered_dir.iterdir():
        if not source_dir.is_dir():
            continue

        source = source_dir.name

        # Load all cache files for this source
        for cache_file in source_dir.glob("*.json"):
            identifier = cache_file.stem

            repos = load_discovered_repos(source, identifier, cache_dir=cache_dir)
            if repos:
                # Deduplicate by owner/name
                for repo in repos:
                    repo_key = f"{repo.owner}/{repo.name}"
                    if repo_key not in seen_repos:
                        all_repos.append(repo)
                        seen_repos.add(repo_key)

    return all_repos


def is_repo_analyzed(owner: str, name: str, cache_dir: Path | None = None) -> bool:
    """Check if a repository has already been analyzed."""
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    project_dir = cache_dir / "projects" / owner / name
    return project_dir.exists() and any(project_dir.glob("*.json"))


def main() -> int:
    """Analyze all discovered repos that haven't been analyzed yet."""
    # Check for verbose flag
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    cache_dir = get_default_cache_dir()

    print("Loading discovered repositories...")
    repos = get_all_discovered_repos(cache_dir=cache_dir)
    print(f"Found {len(repos)} unique repositories across all sources")
    if verbose:
        print("Running in verbose mode (showing fallback attempts)\n")

    analyzed_count = 0
    skipped_count = 0
    error_count = 0

    for repo in repos:
        repo_name = f"{repo.owner}/{repo.name}"

        # Skip if already analyzed
        if is_repo_analyzed(repo.owner, repo.name, cache_dir=cache_dir):
            print(f"  ⏭️  {repo_name} - already analyzed")
            skipped_count += 1
            continue

        print(f"  🔍 {repo_name} - analyzing...")

        try:
            # Analyze with auto-detect
            result = analyze_repository(
                owner=repo.owner,
                repo=repo.name,
                package_spec=None,  # Auto-detect
                cache_dir=cache_dir,
                verbose=verbose,
            )

            if result:
                project_loc = result['project_loc']

                # Check if we have full analysis or partial
                if 'ratio' in result:
                    # Full analysis with dependencies
                    print(f"  ✅ {repo_name} - {project_loc:,} LoC, deps {result['total_loc']:,} LoC, ratio {result['ratio']:.1%}")
                    analyzed_count += 1
                else:
                    # Partial analysis (project LoC only, no package detected)
                    print(f"  📊 {repo_name} - {project_loc:,} LoC (no package detected, dependencies not analyzed)")
                    analyzed_count += 1
            else:
                print(f"  ⚠️  {repo_name} - could not analyze (project LoC unavailable)")
                error_count += 1

        except Exception as e:
            print(f"  ❌ {repo_name} - error: {e}")
            error_count += 1
            continue

    print("\n" + "=" * 60)
    print(f"Analysis complete:")
    print(f"  Analyzed: {analyzed_count}")
    print(f"  Skipped (already analyzed): {skipped_count}")
    print(f"  Errors: {error_count}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
