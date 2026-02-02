import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import typer

from iceberg.calculator import calculate_transitive_loc
from iceberg.cache import get_default_cache_dir, save_trending_repos
from iceberg.depsdev import DepsDevError, get_dependencies, get_project_loc
from iceberg.detector import detect_package
from iceberg.github import fetch_trending_repos
from iceberg.models import PackageIdentifier
from iceberg.sbom import analyze_from_manifest

app = typer.Typer()


@app.command()
def fetch(
    limit: int = typer.Option(10, help="Number of trending repos to fetch"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Fetch trending repositories and cache results."""
    try:
        if cache_dir is None:
            cache_dir = get_default_cache_dir()

        repos = fetch_trending_repos(limit=limit)
        save_trending_repos(repos, cache_dir=cache_dir)

        if json_output:
            data = [repo.model_dump(mode="json") for repo in repos]
            typer.echo(json.dumps(data, indent=2))
        else:
            typer.echo(f"Fetched {len(repos)} trending repositories")
            for repo in repos:
                typer.echo(f"  - {repo.owner}/{repo.name} ({repo.stars:,} stars)")

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

            if not head:
                if not json_output:
                    typer.echo(f"🔍 Finding latest published version...")
                ref_to_analyze = get_latest_published_version(owner, name)
                if ref_to_analyze:
                    version_for_cache = ref_to_analyze
                    if not json_output:
                        typer.echo(f"✓ Found version: {ref_to_analyze}")
                elif not json_output:
                    typer.echo(f"⚠️  No published versions found, using HEAD")
                    version_for_cache = "HEAD"
            else:
                version_for_cache = "HEAD"

            # Check cache first
            cached_project_data = load_project_loc(owner, name, version_for_cache, cache_dir=cache_dir)

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

                    # Save to cache
                    project_data = {
                        "owner": owner,
                        "repo": name,
                        "version": version_for_cache,
                        "loc": project_loc,
                        "source": github_result["source"],
                        "cached_at": datetime.now(timezone.utc).isoformat(),
                        "ref": github_result["metadata"]["ref"],
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


if __name__ == "__main__":
    app()
