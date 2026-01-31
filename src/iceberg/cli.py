import json
import sys
from pathlib import Path

import typer

from iceberg.calculator import calculate_transitive_loc
from iceberg.cache import get_default_cache_dir, save_trending_repos
from iceberg.depsdev import get_project_loc
from iceberg.github import fetch_trending_repos
from iceberg.models import PackageIdentifier

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
    package: str = typer.Option(
        ..., help="Package identifier (system:name:version, e.g., npm:react:18.2.0)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Analyze dependency footprint of a repository."""
    try:
        if cache_dir is None:
            cache_dir = get_default_cache_dir()

        parts = repo.split("/")
        if len(parts) != 2:
            typer.echo("Error: Repository must be in format owner/name", err=True)
            raise typer.Exit(1)

        owner, name = parts

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

        project_loc = get_project_loc(owner, name)
        total_loc = calculate_transitive_loc(pkg, cache_dir=cache_dir)

        if json_output:
            data = {
                "repo": repo,
                "project_loc": project_loc,
                "total_loc": total_loc,
            }
            typer.echo(json.dumps(data, indent=2))
        else:
            typer.echo(f"\nRepository: {repo}")
            if project_loc is not None:
                typer.echo(f"Project LoC: {project_loc:,}")
            else:
                typer.echo("Project LoC: N/A")
            typer.echo(f"Total LoC (with dependencies): {total_loc:,}")

            if project_loc is not None and project_loc > 0:
                ratio = total_loc / project_loc
                typer.echo(f"Dependency multiplier: {ratio:.1f}x")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
