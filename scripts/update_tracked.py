#!/usr/bin/env python3
"""Update all tracked repositories by checking for new versions."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iceberg.calculator import analyze_repository
from iceberg.tracking import load_tracked_repos, needs_update


def main():
    """Update all tracked repositories."""
    cache_dir = Path("cache")
    
    # Load tracked repos
    repos = load_tracked_repos(cache_dir=cache_dir)
    
    if not repos:
        print("No tracked repositories found.")
        print("\nAdd repositories with: iceberg track owner/repo")
        return
    
    print(f"Checking {len(repos)} tracked repositories for updates...\n")
    
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    
    for repo_info in repos:
        owner = repo_info["owner"]
        repo = repo_info["repo"]
        repo_name = f"{owner}/{repo}"
        
        # Check if update needed
        needs_update_result, reason = needs_update(owner, repo, cache_dir=cache_dir)
        
        if not needs_update_result:
            print(f"⏭️  {repo_name} - {reason}")
            skipped_count += 1
            continue
        
        print(f"🔄 {repo_name} - {reason}")
        
        try:
            result = analyze_repository(
                owner=owner,
                repo=repo,
                cache_dir=cache_dir,
                verbose=True,
            )
            
            if result:
                print(f"  ✓ Updated: {result['project_loc']:,} LoC")
                if 'total_loc' in result:
                    print(f"  ✓ Dependencies: {result['total_loc']:,} LoC")
                updated_count += 1
            else:
                print(f"  ✗ Failed to analyze")
                failed_count += 1
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed_count += 1
        
        print()
    
    # Summary
    print("=" * 60)
    print(f"Updated: {updated_count}")
    print(f"Skipped (up to date): {skipped_count}")
    print(f"Failed: {failed_count}")


if __name__ == "__main__":
    main()
