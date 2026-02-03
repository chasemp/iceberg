#!/usr/bin/env python3
"""Periodic maintenance run - keep entire dataset fresh.

This script checks ALL cached repos for staleness and updates as needed.
Designed for weekly or monthly execution.

Staleness Strategy:
- Tracked repos: Check daily, update if HEAD changed
- Popular (stars>10k): Check weekly, update if >7 days old
- Regular repos: Check monthly, update if >30 days old
- Old discoveries (>90 days): Check quarterly, update if >90 days old

Rate Limiting:
- Batches updates in groups
- Respects GitHub API limits
- Configurable max updates per run

Usage:
    python scripts/run_maintenance.py
    python scripts/run_maintenance.py --verbose
    python scripts/run_maintenance.py --max-updates 100
"""

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iceberg.cache import get_default_cache_dir, load_project_loc, save_project_loc
from iceberg.calculator import analyze_repository
from iceberg.tracking import needs_update


def get_all_cached_repos(cache_dir: Path) -> list[dict[str, Any]]:
    """Load all repos from cache with metadata."""
    projects_dir = cache_dir / "projects"
    
    if not projects_dir.exists():
        return []
    
    repos: list[dict[str, Any]] = []
    
    for owner_dir in projects_dir.iterdir():
        if not owner_dir.is_dir():
            continue
        
        owner = owner_dir.name
        
        for repo_dir in owner_dir.iterdir():
            if not repo_dir.is_dir():
                continue
            
            repo = repo_dir.name
            
            # Load HEAD version
            cached = load_project_loc(owner, repo, "HEAD", cache_dir=cache_dir)
            if cached:
                repos.append(cached)
    
    return repos


def calculate_staleness_days(cached_at: str) -> float:
    """Calculate how many days since last analysis."""
    try:
        cached_time = datetime.fromisoformat(cached_at.replace('Z', '+00:00'))
        age = datetime.now(timezone.utc) - cached_time
        return age.total_seconds() / 86400  # Convert to days
    except Exception:
        return 999  # Very old if we can't parse


def should_check_for_updates(repo: dict[str, Any], verbose: bool = False) -> tuple[bool, str]:
    """Determine if a repo should be checked for updates based on staleness strategy.
    
    Returns:
        (should_check: bool, reason: str)
    """
    owner = repo.get("owner", "unknown")
    name = repo.get("repo", "unknown")
    repo_name = f"{owner}/{name}"
    
    cached_at = repo.get("cached_at")
    if not cached_at:
        return (True, "no cached_at timestamp")
    
    # Calculate age
    days_old = calculate_staleness_days(cached_at)
    
    # Checked very recently? Skip regardless of priority
    if days_old < 1:
        return (False, f"analyzed {days_old * 24:.1f}h ago")
    
    # Get metadata
    tracked = repo.get("tracked", False)
    priority = repo.get("maintenance_priority", "low")
    last_discovered = repo.get("last_discovered")
    
    # Was in yesterday's discovery? Already checked
    if last_discovered:
        try:
            discovered_date = datetime.fromisoformat(last_discovered)
            age_since_discovery = datetime.now(timezone.utc) - discovered_date.replace(tzinfo=timezone.utc)
            if age_since_discovery < timedelta(days=1):
                return (False, "in yesterday's discovery")
        except Exception:
            pass
    
    # Staleness thresholds by priority
    if tracked:
        # Tracked repos: check if > 1 day old
        if days_old > 1:
            return (True, f"tracked, {days_old:.1f} days old")
    elif priority == "high" or priority == "medium":
        # Popular repos: check if > 7 days old
        if days_old > 7:
            return (True, f"popular, {days_old:.1f} days old")
    elif priority == "low":
        # Regular repos: check if > 30 days old
        if days_old > 30:
            return (True, f"regular, {days_old:.1f} days old")
    else:
        # Old/unknown: check if > 90 days old
        if days_old > 90:
            return (True, f"old, {days_old:.1f} days old")
    
    return (False, f"not stale ({days_old:.1f} days old)")


def prioritize_repos(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort repos by maintenance priority."""
    def priority_key(repo: dict[str, Any]) -> int:
        if repo.get("tracked"):
            return 0  # Highest priority
        priority = repo.get("maintenance_priority", "low")
        if priority == "high":
            return 1
        elif priority == "medium":
            return 2
        else:
            return 3
    
    return sorted(repos, key=priority_key)


def main():
    """Run maintenance workflow."""
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    
    # Parse max-updates flag
    max_updates = 200  # Default
    for arg in sys.argv:
        if arg.startswith("--max-updates="):
            try:
                max_updates = int(arg.split("=")[1])
            except ValueError:
                pass
    
    cache_dir = get_default_cache_dir()
    
    print("=" * 60)
    print("🔧 MAINTENANCE RUN")
    print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Max updates: {max_updates}")
    print("=" * 60)
    print()
    
    # Step 1: Load all cached repos
    print("📂 Loading cached repositories...")
    all_repos = get_all_cached_repos(cache_dir)
    print(f"Loaded {len(all_repos)} cached repos")
    print()
    
    # Step 2: Filter by staleness
    print("🔍 Filtering by staleness criteria...")
    stale_repos = []
    
    for repo in all_repos:
        should_check, reason = should_check_for_updates(repo, verbose)
        if should_check:
            stale_repos.append((repo, reason))
    
    print(f"Found {len(stale_repos)} stale repos")
    
    if not stale_repos:
        print("\n✓ All repos are up to date!")
        return 0
    
    print()
    
    # Step 3: Prioritize
    print("📊 Prioritizing by maintenance strategy...")
    repos_with_reasons = [(r, reason) for r, reason in stale_repos]
    prioritized = prioritize_repos([r for r, _ in repos_with_reasons])
    
    # Count by priority
    tracked_count = sum(1 for r in prioritized if r.get("tracked"))
    high_count = sum(1 for r in prioritized if r.get("maintenance_priority") == "high" and not r.get("tracked"))
    medium_count = sum(1 for r in prioritized if r.get("maintenance_priority") == "medium")
    low_count = sum(1 for r in prioritized if r.get("maintenance_priority") == "low")
    
    print(f"  Tracked: {tracked_count}")
    print(f"  High priority: {high_count}")
    print(f"  Medium priority: {medium_count}")
    print(f"  Low priority: {low_count}")
    print()
    
    # Step 4: Update repos (up to max_updates)
    print("=" * 60)
    print("🔄 UPDATING REPOS")
    print("=" * 60)
    print()
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for i, repo in enumerate(prioritized):
        if updated_count >= max_updates:
            remaining = len(prioritized) - i
            print(f"\n⚠️  Reached max updates ({max_updates})")
            print(f"   Skipping {remaining} remaining repos")
            break
        
        owner = repo["owner"]
        name = repo["repo"]
        repo_name = f"{owner}/{name}"
        
        # Find reason
        reason = "needs check"
        for r, rsn in stale_repos:
            if r["owner"] == owner and r["repo"] == name:
                reason = rsn
                break
        
        # Check if actually needs updating
        needs_update_result, update_reason = needs_update(owner, name, cache_dir=cache_dir)
        
        if not needs_update_result:
            print(f"⏭️  {repo_name} - {update_reason}")
            skipped_count += 1
            continue
        
        print(f"🔄 {repo_name} - {update_reason}")
        
        try:
            result = analyze_repository(
                owner=owner,
                repo=name,
                cache_dir=cache_dir,
                verbose=verbose,
            )
            
            if result:
                # Update metadata
                cached = load_project_loc(owner, name, "HEAD", cache_dir=cache_dir)
                if cached:
                    # Keep existing metadata but update timestamp
                    save_project_loc(cached, cache_dir=cache_dir)
                
                print(f"  ✓ Updated: {result['project_loc']:,} LoC")
                if 'total_loc' in result:
                    print(f"  ✓ Dependencies: {result['total_loc']:,} LoC")
                updated_count += 1
            else:
                print(f"  ✗ Failed to analyze")
                error_count += 1
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
            error_count += 1
        
        print()
        
        # Rate limiting: sleep briefly between updates
        if updated_count % 10 == 0 and updated_count > 0:
            print(f"💤 Brief pause (rate limiting)...\n")
            time.sleep(2)
    
    # Summary
    print("=" * 60)
    print("📊 MAINTENANCE SUMMARY")
    print("=" * 60)
    print(f"Total cached: {len(all_repos)}")
    print(f"Checked for staleness: {len(stale_repos)}")
    print(f"Updated: {updated_count}")
    print(f"Skipped (up to date): {skipped_count}")
    print(f"Errors: {error_count}")
    print()
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
