"""Analyze command - analyze a single repository."""

import json
from pathlib import Path

import typer

from iceberg.calculator import analyze_repository
from iceberg.commands.helpers import resolve_cache_dir, setup_verbose_logging


def analyze_command(
    repo: str = typer.Argument(..., help="GitHub repository (owner/name)"),
    package: str | None = typer.Option(
        None, help="Package identifier (system:name:version, e.g., npm:react:18.2.0)"
    ),
    auto_detect: bool = typer.Option(
        False, "--auto-detect", help="Auto-detect package from repository"
    ),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Verbose output"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Analyze a GitHub repository's code iceberg.

    Examples:
      iceberg analyze facebook/react
      iceberg analyze facebook/react --package npm:react:18.2.0
      iceberg analyze facebook/react --auto-detect
      iceberg analyze torvalds/linux --json
    """
    setup_verbose_logging(verbose)

    try:
        cache_dir = resolve_cache_dir(cache_dir)

        if "/" not in repo:
            typer.echo("Error: Repository must be in owner/name format", err=True)
            raise typer.Exit(1)

        owner, name = repo.split("/", 1)

        # Ensure repo is tracked if not already discovered
        from iceberg.cache import load_repo_metadata
        from iceberg.tracking import save_tracked_repo

        existing_metadata = load_repo_metadata(owner, name, cache_dir)
        if existing_metadata is None:
            # Repo not in discovery cache, track it automatically
            if not json_output:
                typer.echo(f"Repository not in discovery cache, tracking {owner}/{name}...")
            save_tracked_repo(owner, name, cache_dir)

        # Parse package spec if provided
        package_spec = None
        if package:
            parts = package.split(":")
            if len(parts) != 3:
                typer.echo("Error: Package must be in format system:name:version", err=True)
                raise typer.Exit(1)
            package_spec = {"system": parts[0], "name": parts[1], "version": parts[2]}

        # Analyze the repository
        if not json_output:
            typer.echo(f"Analyzing {owner}/{name}...")

        result = analyze_repository(
            owner=owner,
            repo=name,
            package_spec=package_spec if not auto_detect else None,
            cache_dir=cache_dir,
        )

        if result:
            if json_output:
                typer.echo(json.dumps(result, indent=2))
            else:
                typer.echo(f"\nResults for {owner}/{name}:")
                typer.echo(f"  Project LoC: {result['project_loc']:,}")
                if "total_loc" in result:
                    typer.echo(f"  Dependencies LoC: {result['total_loc']:,}")
                    typer.echo(f"  Iceberg Ratio: {result['ratio']:.1%}")
                else:
                    typer.echo(f"  Dependencies: Could not analyze")
                if "ai_tools" in result and result["ai_tools"]:
                    typer.echo(f"  AI Tools Detected: {', '.join(result['ai_tools'])}")
        else:
            typer.echo(f"Could not analyze {owner}/{name}", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
