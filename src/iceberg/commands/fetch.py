"""Fetch command - discover repositories from various sources."""

import json
import os
from pathlib import Path
from typing import Literal

import typer

from iceberg.cache import save_repo_metadata
from iceberg.commands.helpers import resolve_cache_dir, setup_verbose_logging
from iceberg.github import fetch_trending_repos
from iceberg.github_ranking import fetch_github_ranking
from iceberg.github_search import build_search_query, search_repositories


def fetch_command(
    limit: int = typer.Option(25, help="Number of repositories to fetch"),
    source: Literal["trending", "search", "github-ranking"] = typer.Option(
        "trending", help="Repository source (trending, search, or github-ranking)"
    ),
    category: str = typer.Option(
        "Top-100-stars", help="Category for github-ranking (e.g., Python, JavaScript, Top-100-stars)"
    ),
    stars: str | None = typer.Option(
        None, help="Star count filter, e.g., '>1000' (with --source search)"
    ),
    language: str | None = typer.Option(
        None, help="Language filter (with --source search)"
    ),
    created: str | None = typer.Option(
        None, help="Created date filter, e.g., '>2024-01-01' (with --source search)"
    ),
    pushed: str | None = typer.Option(
        None, help="Last push date filter (with --source search)"
    ),
    query: str | None = typer.Option(
        None, help="Custom search query (with --source search)"
    ),
    analyze_repos: bool = typer.Option(False, "--analyze", help="Analyze each repo after fetching"),
    head: bool = typer.Option(False, "--head", help="Analyze HEAD instead of latest published version (with --analyze)"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Verbose output"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Fetch repositories from trending, search, or github-ranking.

    Examples:
      iceberg fetch --limit 10
      iceberg fetch --source search --stars ">10000" --limit 50
      iceberg fetch --source search --language python --stars ">5000"
      iceberg fetch --source search --query "language:rust stars:>1000"
      iceberg fetch --source github-ranking --category Python --limit 50
      iceberg fetch --source github-ranking --category Top-100-stars --limit 100

    Use --analyze to automatically analyze each fetched repository.
    Results are cached, so re-running will skip already analyzed repos.
    """
    setup_verbose_logging(verbose)

    try:
        cache_dir = resolve_cache_dir(cache_dir)

        # Fetch repos based on source
        if source == "trending":
            repos = fetch_trending_repos(limit=limit)
        elif source == "github-ranking":
            repos = fetch_github_ranking(category=category, limit=limit)
        else:  # search
            query_str = query or build_search_query(
                stars=stars, language=language, created=created, pushed=pushed
            )
            token = os.environ.get("GITHUB_TOKEN")
            repos = search_repositories(query_str, limit=limit, token=token)

        # Save to repo metadata structure
        for repo in repos:
            save_repo_metadata(repo, repo.source, cache_dir=cache_dir)

        if json_output:
            data = [repo.model_dump(mode="json") for repo in repos]
            typer.echo(json.dumps(data, indent=2))
        else:
            _display_fetch_results(repos, limit)

        # Analyze repos if requested
        if analyze_repos and not json_output:
            _analyze_fetched_repos(repos, head, cache_dir)

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def _display_fetch_results(repos: list, limit: int) -> None:
    """Display fetched repositories in human-readable format."""
    if repos:
        repo_source = repos[0].source
        if repo_source.startswith("trending"):
            timeframe = repo_source.replace("trending-", "")
            if len(repos) < limit:
                typer.echo(f"Fetched {len(repos)} {timeframe} trending repositories (GitHub only shows ~{len(repos)} on trending page)")
            else:
                typer.echo(f"Fetched {len(repos)} {timeframe} trending repositories")
        elif repo_source.startswith("github-ranking"):
            category_name = repo_source.replace("github-ranking-", "")
            typer.echo(f"Fetched {len(repos)} repositories from GitHub-Ranking ({category_name})")
        elif repo_source == "search":
            typer.echo(f"Fetched {len(repos)} repositories from search")
            if repos[0].search_query:
                typer.echo(f"Query: {repos[0].search_query}")
        else:
            typer.echo(f"Fetched {len(repos)} repositories")

        for repo in repos:
            typer.echo(f"  - {repo.owner}/{repo.name} ({repo.stars:,} stars)")


def _analyze_fetched_repos(repos: list, head: bool, cache_dir: Path) -> None:
    """Analyze fetched repositories."""
    from iceberg.cache import load_project_loc
    from iceberg.calculator import analyze_repository
    from iceberg.github_loc import get_current_head_hash, get_latest_published_version

    typer.echo(f"\nAnalyzing {len(repos)} repositories...\n")

    for i, repo in enumerate(repos, 1):
        typer.echo(f"[{i}/{len(repos)}] {repo.owner}/{repo.name}")

        # Determine version to analyze
        ref_to_analyze: str | None = None
        version_for_cache: str = "HEAD"
        use_commit_hash = False

        if not head:
            ref_to_analyze = get_latest_published_version(repo.owner, repo.name)
            if ref_to_analyze:
                version_for_cache = ref_to_analyze
            else:
                version_for_cache = "HEAD"
                use_commit_hash = True
        else:
            version_for_cache = "HEAD"
            use_commit_hash = True

        # Check if already analyzed
        cache_lookup_version = version_for_cache
        if use_commit_hash:
            current_hash = get_current_head_hash(repo.owner, repo.name)
            if current_hash:
                cache_lookup_version = current_hash

        cached = load_project_loc(repo.owner, repo.name, cache_lookup_version, cache_dir=cache_dir)

        if cached:
            typer.echo(f"  ✓ Already analyzed ({version_for_cache}, {cached['loc']:,} LoC)\n")
            continue

        # Analyze the repo
        try:
            result = analyze_repository(
                owner=repo.owner,
                repo=repo.name,
                package_spec=None,  # Auto-detect
                cache_dir=cache_dir,
            )

            if result:
                typer.echo(f"  ✓ Project: {result['project_loc']:,} LoC")
                if 'total_loc' in result:
                    typer.echo(f"  ✓ Dependencies: {result['total_loc']:,} LoC")
                    typer.echo(f"  ✓ Iceberg Ratio: {result['ratio']:.1%}\n")
                else:
                    typer.echo(f"  ✗ Dependencies: Could not analyze\n")
            else:
                typer.echo(f"  ✗ Could not analyze\n")
        except Exception as ex:
            typer.echo(f"  ✗ Error: {ex}\n")
