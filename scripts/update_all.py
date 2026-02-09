#!/usr/bin/env python3
"""Run the complete data update workflow locally.

This script replicates the GitHub Actions workflow for local development:
1. Fetch trending repos (weekly, monthly)
2. Fetch search queries (highly starred, by language)
3. Analyze all discovered repos
4. Export data for SPA

Usage:
    python update_all.py              # Quiet mode
    python update_all.py -v           # Verbose mode (shows fallback attempts)
    python update_all.py --verbose    # Verbose mode (shows fallback attempts)
    python update_all.py --fresh-all  # Clear all caches and start fresh
    python update_all.py -v --fresh-all # Verbose + fresh start

Run this to update all data manually without GitHub Actions.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'=' * 60}")
    print(f"▶️  {description}")
    print(f"{'=' * 60}")
    print(f"Running: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=True, text=True)
        print(f"✅ {description} - complete")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - failed with exit code {e.returncode}")
        return False


def main() -> int:
    """Run the complete workflow."""
    # Check for flags
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    fresh_all = "--fresh-all" in sys.argv

    print("🚀 Starting complete data update workflow")
    print("=" * 60)
    if verbose:
        print("Running in verbose mode (showing fallback attempts)")
    if fresh_all:
        print("Running in FRESH mode (clearing all caches)")

    # Clear all caches if --fresh-all flag is set
    if fresh_all:
        cache_dirs = [
            Path("cache/discovered"),
            Path("cache/projects"),
            Path("cache/dependencies"),
            Path("cache/loc"),
        ]

        print("\n🗑️  Clearing caches...")
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                print(f"  Removing {cache_dir}/")
                shutil.rmtree(cache_dir)
        print("✅ All caches cleared\n")

    # Track success/failure
    failures = []

    # 1. Fetch trending repos (weekly)
    if not run_command(
        ["iceberg", "fetch", "--source", "trending", "--since", "weekly", "--limit", "25"],
        "Fetch trending repos (weekly)",
    ):
        failures.append("Fetch trending weekly")

    # 2. Fetch trending repos (monthly)
    if not run_command(
        ["iceberg", "fetch", "--source", "trending", "--since", "monthly", "--limit", "25"],
        "Fetch trending repos (monthly)",
    ):
        failures.append("Fetch trending monthly")

    # Check if GITHUB_TOKEN is set
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("\n⚠️  GITHUB_TOKEN not set - skipping search queries (will hit rate limits)")
        print("Set GITHUB_TOKEN env var for higher rate limits (30 req/min vs 10 req/min)")
    else:
        print(f"\n✅ GITHUB_TOKEN found - using authenticated requests")

    # 4. Fetch search - highly starred
    if not run_command(
        ["iceberg", "fetch", "--source", "search", "--stars", ">10000", "--limit", "50"],
        "Fetch search - highly starred",
    ):
        failures.append("Fetch search highly starred")

    # 5. Fetch search - Python highly starred
    if not run_command(
        ["iceberg", "fetch", "--source", "search", "--language", "python", "--stars", ">5000", "--limit", "30"],
        "Fetch search - Python highly starred",
    ):
        failures.append("Fetch search Python")

    # 6. Fetch search - JavaScript highly starred
    if not run_command(
        ["iceberg", "fetch", "--source", "search", "--language", "javascript", "--stars", ">5000", "--limit", "30"],
        "Fetch search - JavaScript highly starred",
    ):
        failures.append("Fetch search JavaScript")

    # 7. Fetch search - Rust highly starred
    if not run_command(
        ["iceberg", "fetch", "--source", "search", "--language", "rust", "--stars", ">3000", "--limit", "30"],
        "Fetch search - Rust highly starred",
    ):
        failures.append("Fetch search Rust")

    # 8. Analyze discovered repos
    script_dir = Path(__file__).parent
    analyze_script = script_dir / "analyze_all_discovered.py"

    analyze_cmd = ["python", str(analyze_script)]
    if verbose:
        analyze_cmd.append("-v")

    if not run_command(
        analyze_cmd,
        "Analyze discovered repos",
    ):
        print("⚠️  Analysis had errors (continuing...)")
        # Don't add to failures - analysis script handles errors gracefully

    # 9. Export data for SPA
    if not run_command(
        ["iceberg", "export", "--output-dir", "./spa/data"],
        "Export data for SPA",
    ):
        failures.append("Export data")

    # Summary
    print("\n" + "=" * 60)
    print("🏁 Workflow complete")
    print("=" * 60)

    if failures:
        print(f"\n❌ {len(failures)} step(s) failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    else:
        print("\n✅ All steps completed successfully!")
        print("\nNext steps:")
        print("  - Review updated cache in cache/discovered/")
        print("  - Review analyzed projects in cache/projects/")
        print("  - Review exported SPA data in spa/data/")
        print("  - Commit and push changes")
        return 0


if __name__ == "__main__":
    sys.exit(main())
