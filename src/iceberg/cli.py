import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import typer

from iceberg.calculator import calculate_transitive_loc
from iceberg.cache import (
    get_default_cache_dir,
    save_discovered_repos,
    save_repo_metadata,
    save_trending_repos,
)
from iceberg.depsdev import DepsDevError, get_dependencies, get_project_loc
from iceberg.detector import detect_package
from iceberg.export import export_all
from iceberg.github import fetch_trending_repos
from iceberg.github_ranking import fetch_github_ranking
from iceberg.github_search import build_search_query, search_repositories
from iceberg.models import PackageIdentifier
from iceberg.sbom import analyze_from_manifest

app = typer.Typer()


@app.command()
def fetch(
    limit: int = typer.Option(25, help="Number of repositories to fetch"),
    source: Literal["trending", "search", "github-ranking"] = typer.Option(
        "trending", help="Repository source (trending, search, or github-ranking)"
    ),
    since: Literal["weekly", "monthly"] = typer.Option(
        "monthly", help="Trending timeframe (with --source trending)"
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
      iceberg fetch --source trending --since weekly --limit 25
      iceberg fetch --source search --stars ">10000" --limit 50
      iceberg fetch --source search --language python --stars ">5000"
      iceberg fetch --source search --query "language:rust stars:>1000"
      iceberg fetch --source github-ranking --category Python --limit 50
      iceberg fetch --source github-ranking --category Top-100-stars --limit 100

    Use --analyze to automatically analyze each fetched repository.
    Results are cached, so re-running will skip already analyzed repos.
    """
    try:
        if cache_dir is None:
            cache_dir = get_default_cache_dir()

        # Fetch repos based on source
        if source == "trending":
            repos = fetch_trending_repos(limit=limit, since=since)
        elif source == "github-ranking":
            repos = fetch_github_ranking(category=category, limit=limit)
        else:  # search
            query_str = query or build_search_query(
                stars=stars, language=language, created=created, pushed=pushed
            )
            token = os.environ.get("GITHUB_TOKEN")
            repos = search_repositories(query_str, limit=limit, token=token)

        save_discovered_repos(repos, cache_dir=cache_dir)

        # Also save to new repo metadata structure
        for repo in repos:
            save_repo_metadata(repo, repo.source, cache_dir=cache_dir)

        if json_output:
            data = [repo.model_dump(mode="json") for repo in repos]
            typer.echo(json.dumps(data, indent=2))
        else:
            # Display source information
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

        # Analyze repos if requested
        if analyze_repos and not json_output:
            from iceberg.cache import load_project_loc
            from iceberg.github_loc import get_current_head_hash, get_github_project_loc, get_latest_published_version

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

                # Check if already analyzed (use commit hash for HEAD)
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
                    from iceberg.calculator import analyze_repository

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

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def analyze(
    repo: str = typer.Argument(..., help="GitHub repository (owner/name)"),
    package: str | None = typer.Option(
        None, help="Package identifier (system:name:version, e.g., npm:react:18.2.0)"
    ),
    auto_detect: bool = typer.Option(
        False, "--auto-detect", help="Auto-detect package from repository"
    ),
    head: bool = typer.Option(
        False, "--head", help="Analyze HEAD instead of latest published version"
    ),
    verbose: int = typer.Option(
        0, "-v", "--verbose", count=True, help="Verbose output (-v shows dependencies, -vv enables debug logging)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Analyze dependency footprint of a repository.

    By default, analyzes the latest published version (git tag).
    Use --head to analyze the current HEAD commit instead.

    Verbosity levels:
      (none)  Clean summary output
      -v      Show dependency breakdown
      -vv     Enable debug logging
    """
    # Configure logging based on verbosity
    if verbose >= 2:
        logging.basicConfig(
            level=logging.DEBUG,
            format="[DEBUG] %(name)s: %(message)s",
        )
        logging.debug("Debug logging enabled")
    elif verbose >= 1:
        logging.basicConfig(level=logging.INFO)

    try:
        if cache_dir is None:
            cache_dir = get_default_cache_dir()

        parts = repo.split("/")
        if len(parts) != 2:
            typer.echo("Error: Repository must be in format owner/name", err=True)
            raise typer.Exit(1)

        owner, name = parts

        if auto_detect or package is None:
            if not json_output:
                typer.echo(f"🔍 Auto-detecting package for {owner}/{name}...")

            detected_pkg = detect_package(owner, name)

            if detected_pkg is None:
                typer.echo(
                    f"Error: Could not detect package for {owner}/{name}. "
                    "Please provide --package manually.",
                    err=True,
                )
                raise typer.Exit(1)

            pkg = detected_pkg

            if not json_output:
                typer.echo(
                    f"✓ Detected: {pkg.system}:{pkg.name}:{pkg.version}\n"
                )
        else:
            pkg_parts = package.split(":")
            if len(pkg_parts) != 3:
                typer.echo(
                    "Error: Package must be in format system:name:version", err=True
                )
                raise typer.Exit(1)

            system, pkg_name, version = pkg_parts

            pkg = PackageIdentifier(
                system=system,  # type: ignore[arg-type]
                name=pkg_name,
                version=version,
            )

        # Try to get project LoC from deps.dev first
        try:
            project_loc = get_project_loc(owner, name)
        except Exception:
            project_loc = None

        # If deps.dev doesn't have project LoC, try cloning and counting
        if project_loc is None:
            from iceberg.cache import load_project_loc, save_project_loc
            from iceberg.github_loc import get_github_project_loc, get_latest_published_version

            # Determine which ref to analyze (default to published, unless --head)
            ref_to_analyze: str | None = None
            version_for_cache: str = "HEAD"
            use_commit_hash_for_cache = False

            if not head:
                if not json_output:
                    typer.echo(f"🔍 Finding latest published version...")
                ref_to_analyze = get_latest_published_version(owner, name)
                if ref_to_analyze:
                    version_for_cache = ref_to_analyze
                    if not json_output:
                        typer.echo(f"✓ Found version: {ref_to_analyze}")
                else:
                    if not json_output:
                        typer.echo(f"⚠️  No published versions found, using HEAD")
                    version_for_cache = "HEAD"
                    use_commit_hash_for_cache = True
            else:
                version_for_cache = "HEAD"
                use_commit_hash_for_cache = True

            # Check cache first
            # For HEAD, use current commit hash as cache key
            cache_lookup_version = version_for_cache
            if use_commit_hash_for_cache:
                from iceberg.github_loc import get_current_head_hash
                current_hash = get_current_head_hash(owner, name)
                if current_hash:
                    cache_lookup_version = current_hash

            cached_project_data = load_project_loc(owner, name, cache_lookup_version, cache_dir=cache_dir)

            if cached_project_data:
                project_loc = cached_project_data["loc"]
                if not json_output:
                    typer.echo(f"✓ Loaded {version_for_cache} from cache\n")
            else:
                # Not in cache, need to clone and count
                if not json_output:
                    ref_msg = f" at {ref_to_analyze}" if ref_to_analyze else ""
                    typer.echo(f"⏳ Cloning repository{ref_msg} to count project LoC...")

                github_result = get_github_project_loc(owner, name, cache_dir=cache_dir, ref=ref_to_analyze)
                if github_result:
                    project_loc = github_result["loc"]

                    # Use commit hash as cache key if analyzing HEAD
                    commit_hash = github_result["metadata"].get("commit_hash")
                    cache_version = version_for_cache
                    if use_commit_hash_for_cache and commit_hash:
                        cache_version = commit_hash[:8]  # Use short hash

                    # Save to cache
                    project_data = {
                        "owner": owner,
                        "repo": name,
                        "version": cache_version,
                        "loc": project_loc,
                        "source": github_result["source"],
                        "cached_at": datetime.now(timezone.utc).isoformat(),
                        "ref": github_result["metadata"]["ref"],
                        "commit_hash": commit_hash,
                        "repo_url": github_result["metadata"]["repo_url"],
                        "clone_duration_seconds": github_result["metadata"]["clone_duration_seconds"],
                        "count_duration_seconds": github_result["metadata"]["count_duration_seconds"],
                    }
                    save_project_loc(project_data, cache_dir=cache_dir)

                    if not json_output:
                        clone_time = github_result["metadata"]["clone_duration_seconds"]
                        count_time = github_result["metadata"]["count_duration_seconds"]
                        ref = github_result["metadata"]["ref"]
                        typer.echo(
                            f"✓ Cloned and counted {ref} in {clone_time + count_time:.2f}s (cached)\n"
                        )

        try:
            total_loc = calculate_transitive_loc(pkg, cache_dir=cache_dir)
            analysis_method = "published package"
        except (DepsDevError, Exception):
            if not json_output:
                typer.echo(
                    f"📦 Using manifest-based dependency analysis\n"
                )

            sbom_result = analyze_from_manifest(owner, name, cache_dir=cache_dir)

            if sbom_result is None:
                typer.echo(
                    "Error: Could not find manifest file (package.json, pyproject.toml, etc.)",
                    err=True,
                )
                raise typer.Exit(1)

            total_loc = sbom_result["total_dependencies_loc"]
            analysis_method = "SBOM (manifest)"

            # Only show dependency list if verbose
            if not json_output and verbose >= 1 and len(sbom_result["dependencies"]) > 0:
                typer.echo(f"\nFound {len(sbom_result['dependencies'])} dependencies:\n")
                for dep in sbom_result["dependencies"][:5]:
                    typer.echo(f"  - {dep['name']}@{dep['version']}: {dep['loc']:,} LoC")
                if len(sbom_result["dependencies"]) > 5:
                    typer.echo(f"  ... and {len(sbom_result['dependencies']) - 5} more\n")

        if json_output:
            data = {
                "repo": repo,
                "project_loc": project_loc,
                "total_loc": total_loc,
                "analysis_method": analysis_method,
            }
            typer.echo(json.dumps(data, indent=2))
        else:
            typer.echo(f"\nRepository: {repo}")
            typer.echo(f"Analysis method: {analysis_method}")

            if project_loc is not None:
                typer.echo(f"Project LoC: {project_loc:,}")
            else:
                typer.echo("Project LoC: N/A")

            typer.echo(f"Total LoC (with dependencies): {total_loc:,}")

            if project_loc is not None and project_loc > 0:
                deps_only = total_loc - project_loc
                iceberg_ratio = deps_only / project_loc
                project_pct = (project_loc / total_loc) * 100
                typer.echo(f"\nIceberg effect:")
                typer.echo(f"  Your code: {project_pct:.1f}% of total")
                typer.echo(f"  Iceberg ratio: {iceberg_ratio:.1f}x (dependencies/project)")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def track(
    repo_spec: str = typer.Argument(..., help="Repository in format owner/repo"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Track a repository for continuous updates.

    Adds a repository to the tracking list. Tracked repositories will be
    checked for updates when running the workflow and re-analyzed if newer
    versions are available.

    Example: iceberg track facebook/react
    """
    from iceberg.tracking import save_tracked_repo, is_repo_tracked

    try:
        parts = repo_spec.split("/")
        if len(parts) != 2:
            typer.echo("Error: Repository must be in format owner/repo", err=True)
            raise typer.Exit(1)

        owner, repo = parts

        if is_repo_tracked(owner, repo, cache_dir=cache_dir):
            typer.echo(f"✓ {owner}/{repo} is already being tracked")
            return

        save_tracked_repo(owner, repo, cache_dir=cache_dir)
        typer.echo(f"✓ Now tracking {owner}/{repo}")
        typer.echo(f"  Run analysis with: iceberg analyze {owner}/{repo}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def untrack(
    repo_spec: str = typer.Argument(..., help="Repository in format owner/repo"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Stop tracking a repository.

    Removes a repository from the tracking list. This does not delete
    cached analysis data.

    Example: iceberg untrack facebook/react
    """
    from iceberg.tracking import remove_tracked_repo, is_repo_tracked

    try:
        parts = repo_spec.split("/")
        if len(parts) != 2:
            typer.echo("Error: Repository must be in format owner/repo", err=True)
            raise typer.Exit(1)

        owner, repo = parts

        if not is_repo_tracked(owner, repo, cache_dir=cache_dir):
            typer.echo(f"⚠️  {owner}/{repo} is not being tracked")
            return

        remove_tracked_repo(owner, repo, cache_dir=cache_dir)
        typer.echo(f"✓ Stopped tracking {owner}/{repo}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def list_tracked(
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all tracked repositories.

    Shows repositories that are being tracked for continuous updates.
    """
    from iceberg.tracking import load_tracked_repos

    try:
        repos = load_tracked_repos(cache_dir=cache_dir)

        if json_output:
            typer.echo(json.dumps({"repositories": repos}, indent=2))
            return

        if not repos:
            typer.echo("No repositories are being tracked.")
            typer.echo("\nAdd a repository with: iceberg track owner/repo")
            return

        typer.echo(f"Tracking {len(repos)} repositories:\n")
        for repo in repos:
            owner = repo["owner"]
            name = repo["repo"]
            added_at = repo.get("added_at", "unknown")
            typer.echo(f"  - {owner}/{name}")
            if added_at != "unknown":
                typer.echo(f"    Added: {added_at}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()



@app.command()
def export(
    output_dir: Path = typer.Option("./spa/data", help="Output directory for exported JSON files"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Export cached data to SPA-friendly JSON format.
    
    Transforms the internal cache into JSON files optimized for
    the GitHub Pages SPA, enabling interactive visualization.
    """
    try:
        typer.echo(f"Exporting data to {output_dir}...")
        
        results = export_all(output_dir, cache_dir=cache_dir)
        
        typer.echo(f"✓ Exported {results['discovery_index']['dimensions_exported']} discovery dimensions")
        typer.echo(f"✓ Exported {results['repository_details']['repos_exported']} repository details")
        typer.echo(f"✓ Exported {results['dependency_graphs']['graphs_exported']} dependency graphs")
        typer.echo(f"✓ Exported {results['dependency_rankings']['packages_exported']} dependency rankings")
        typer.echo(f"\nData exported to: {output_dir}")
        
    except Exception as e:
        typer.echo(f"Error exporting data: {e}", err=True)
        raise typer.Exit(1)

