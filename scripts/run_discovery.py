#!/usr/bin/env python3
"""Daily discovery run - find new repos and update current batch.

This script is designed for daily execution (e.g., GitHub Actions).
It fetches the latest trending and search results, then analyzes
new repos and updates existing ones that appear in today's discovery.

Logic:
1. Fetch trending (daily, weekly, monthly)
2. Fetch search queries (stars>5000, language filters)
3. Deduplicate → typically 50-100 unique repos
4. For each repo:
   - If NEW → analyze
   - If EXISTS + in today's discovery → check for updates
   - If EXISTS + analyzed < 24h → skip (already fresh)
5. Mark repos with discovery metadata

Usage:
    python scripts/run_discovery.py
    python scripts/run_discovery.py --verbose
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iceberg.cache import get_default_cache_dir, save_discovered_repos
from iceberg.calculator import analyze_repository
from iceberg.github import fetch_trending_repos
from iceberg.github_search import build_search_query, search_repositories
from iceberg.models import DiscoveredRepo
from iceberg.tracking import is_repo_tracked, load_project_loc, needs_update


def fetch_all_discovery_sources() -> list[DiscoveredRepo]:
    """Fetch repos from all discovery sources."""
    all_repos: list[DiscoveredRepo] = []
    
    print("📡 Fetching discovery sources...\n")
    
    # Trending
    for timeframe in ["daily", "weekly", "monthly"]:
        try:
            print(f"  Fetching trending {timeframe}...")
            repos = fetch_trending_repos(limit=25, since=timeframe)
            all_repos.extend(repos)
            print(f"  ✓ Got {len(repos)} repos from trending {timeframe}")
        except Exception as e:
            print(f"  ✗ Failed to fetch trending {timeframe}: {e}")
    
    print()
    
    # Search - popular JavaScript repos
    try:
        print(f"  Fetching search: stars>10000 language:javascript...")
        query = build_search_query(stars=">10000", language="javascript")
        repos = search_repositories(query, limit=50)
        all_repos.extend(repos)
        print(f"  ✓ Got {len(repos)} repos from search")
    except Exception as e:
        print(f"  ✗ Failed to fetch search: {e}")
    
    # Search - popular Python repos
    try:
        print(f"  Fetching search: stars>10000 language:python...")
        query = build_search_query(stars=">10000", language="python")
        repos = search_repositories(query, limit=50)
        all_repos.extend(repos)
        print(f"  ✓ Got {len(repos)} repos from search")
    except Exception as e:
        print(f"  ✗ Failed to fetch search: {e}")
    
    return all_repos


def deduplicate_repos(repos: list[DiscoveredRepo]) -> list[DiscoveredRepo]:
    """Deduplicate repos by owner/name, keeping first occurrence."""
    seen: set[str] = set()
    unique: list[DiscoveredRepo] = []
    
    for repo in repos:
        key = f"{repo.owner}/{repo.name}"
        if key not in seen:
            seen.add(key)
            unique.append(repo)
    
    return unique


def should_analyze(
    repo: DiscoveredRepo, 
    cache_dir: Path,
    verbose: bool = False
) -> tuple[bool, str]:
    """Determine if a repo should be analyzed.
    
    Returns:
        (should_analyze: bool, reason: str)
    """
    repo_name = f"{repo.owner}/{repo.name}"
    
    # Check if already cached
    cached = load_project_loc(repo.owner, repo.name, "HEAD", cache_dir=cache_dir)
    
    if not cached:
        return (True, "new repo")
    
    # Check if analyzed very recently (< 24h)
    cached_at = cached.get("cached_at")
    if cached_at:
        from datetime import datetime, timedelta
        try:
            cached_time = datetime.fromisoformat(cached_at.replace('Z', '+00:00'))
            age = datetime.now(timezone.utc) - cached_time
            
            if age < timedelta(hours=24):
                return (False, f"analyzed {age.total_seconds() / 3600:.1f}h ago")
        except Exception:
            pass
    
    # Check for updates
    needs_update_result, reason = needs_update(repo.owner, repo.name, cache_dir=cache_dir)
    
    if needs_update_result:
        return (True, f"needs update: {reason}")
    
    return (False, "up to date")


def main():
    """Run discovery workflow."""
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    cache_dir = get_default_cache_dir()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    print("=" * 60)
    print("🔍 DISCOVERY RUN")
    print(f"Date: {today}")
    print("=" * 60)
    print()
    
    # Step 1: Fetch from all sources
    all_repos = fetch_all_discovery_sources()
    print(f"\n📊 Total repos fetched: {len(all_repos)}")
    
    # Step 2: Deduplicate
    unique_repos = deduplicate_repos(all_repos)
    print(f"📊 Unique repos: {len(unique_repos)}")
    print()
    
    # Step 3: Save discovery snapshots (for cache)
    # Group by source and save
    sources: dict[str, list[DiscoveredRepo]] = {}
    for repo in unique_repos:
        source = repo.source
        if source not in sources:
            sources[source] = []
        sources[source].append(repo)
    
    print("💾 Saving discovery snapshots...")
    for source, repos in sources.items():
        save_discovered_repos(repos, cache_dir=cache_dir)
        print(f"  ✓ Saved {len(repos)} repos to {source}")
    print()
    
    # Step 4: Analyze repos
    print("=" * 60)
    print("🔬 ANALYZING REPOS")
    print("=" * 60)
    print()
    
    analyzed_count = 0
    skipped_count = 0
    error_count = 0
    
    for repo in unique_repos:
        repo_name = f"{repo.owner}/{repo.name}"
        
        # Determine if we should analyze
        should_analyze_result, reason = should_analyze(repo, cache_dir, verbose)
        
        if not should_analyze_result:
            print(f"⏭️  {repo_name} - {reason}")
            skipped_count += 1
            continue
        
        print(f"🔍 {repo_name} - {reason}")
        
        try:
            result = analyze_repository(
                owner=repo.owner,
                repo=repo.name,
                cache_dir=cache_dir,
                verbose=verbose,
            )
            
            if result:
                # Add discovery metadata
                from iceberg.cache import load_project_loc, save_project_loc
                cached = load_project_loc(repo.owner, repo.name, "HEAD", cache_dir=cache_dir)
                if cached:
                    cached["last_discovered"] = today
                    cached["discovery_source"] = repo.source
                    cached["tracked"] = is_repo_tracked(repo.owner, repo.name, cache_dir=cache_dir)
                    
                    # Determine priority
                    if cached["tracked"]:
                        cached["maintenance_priority"] = "high"
                    elif repo.stars > 10000:
                        cached["maintenance_priority"] = "medium"
                    else:
                        cached["maintenance_priority"] = "low"
                    
                    save_project_loc(cached, cache_dir=cache_dir)
                
                print(f"  ✓ Analyzed: {result['project_loc']:,} LoC")
                if 'total_loc' in result:
                    print(f"  ✓ Dependencies: {result['total_loc']:,} LoC")
                analyzed_count += 1
            else:
                print(f"  ✗ Failed to analyze")
                error_count += 1
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            error_count += 1
        
        print()
    
    # Summary
    print("=" * 60)
    print("📊 DISCOVERY SUMMARY")
    print("=" * 60)
    print(f"Discovered: {len(unique_repos)} unique repos")
    print(f"Analyzed: {analyzed_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Errors: {error_count}")
    print()
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
