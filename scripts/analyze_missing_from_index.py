#!/usr/bin/env python3
"""Analyze repos from index.json that don't have analysis files yet."""

import json
import sys
from pathlib import Path

from iceberg.cache import get_default_cache_dir
from iceberg.calculator import analyze_repository


def get_repos_from_index(index_path: Path) -> list[tuple[str, str]]:
    """Extract all unique repos from index.json."""
    with open(index_path) as f:
        data = json.load(f)

    repos = set()
    for dimension in data['dimensions']:
        if dimension['type'] == 'trending' and 'snapshots' in dimension:
            for snapshot in dimension['snapshots']:
                for repo in snapshot.get('repos', []):
                    repos.add((repo['owner'], repo['name']))
        elif dimension['type'] == 'search' and 'repos' in dimension:
            for repo in dimension['repos']:
                repos.add((repo['owner'], repo['name']))

    return sorted(repos)


def is_repo_analyzed(owner: str, name: str, cache_dir: Path) -> bool:
    """Check if analysis file exists."""
    project_dir = cache_dir / "projects" / owner / name
    return project_dir.exists() and any(project_dir.glob("*.json"))


def main():
    cache_dir = get_default_cache_dir()
    index_path = Path("spa/data/index.json")

    if not index_path.exists():
        print(f"Error: {index_path} not found")
        return 1

    print("Loading repos from index.json...")
    all_repos = get_repos_from_index(index_path)
    print(f"Found {len(all_repos)} unique repositories in index\n")

    # Find repos that need analysis
    missing = []
    for owner, name in all_repos:
        if not is_repo_analyzed(owner, name, cache_dir):
            missing.append((owner, name))

    print(f"Found {len(missing)} repos without analysis\n")

    if not missing:
        print("All repos are already analyzed!")
        return 0

    analyzed = 0
    errors = 0

    for owner, name in missing:
        repo_name = f"{owner}/{name}"
        print(f"  🔍 {repo_name} - analyzing...")

        try:
            result = analyze_repository(
                owner=owner,
                repo=name,
                package_spec=None,
                cache_dir=cache_dir,
                verbose=False,
            )

            if result:
                project_loc = result['project_loc']
                if 'ratio' in result:
                    print(f"  ✅ {repo_name} - {project_loc:,} LoC, deps {result['total_loc']:,} LoC, ratio {result['ratio']:.1%}")
                else:
                    print(f"  📊 {repo_name} - {project_loc:,} LoC (no package detected)")
                analyzed += 1
            else:
                print(f"  ⚠️  {repo_name} - could not analyze")
                errors += 1
        except Exception as e:
            print(f"  ❌ {repo_name} - error: {e}")
            errors += 1

    print("\n" + "=" * 60)
    print(f"Analysis complete:")
    print(f"  Analyzed: {analyzed}")
    print(f"  Errors: {errors}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
