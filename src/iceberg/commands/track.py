"""Track commands - manage repository tracking."""

import json
from pathlib import Path

import typer

from iceberg.commands.helpers import resolve_cache_dir, setup_verbose_logging
from iceberg.repository_store import RepositoryStore
from iceberg.tracking import is_repo_tracked, load_tracked_repos, remove_tracked_repo, save_tracked_repo


def track_command(
    repo: str = typer.Argument(..., help="Repository to track (owner/name)"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Verbose output"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Add a repository to continuous tracking.

    Examples:
      iceberg track facebook/react
      iceberg track torvalds/linux
    """
    setup_verbose_logging(verbose)

    try:
        cache_dir = resolve_cache_dir(cache_dir)

        if "/" not in repo:
            typer.echo("Error: Repository must be in owner/name format", err=True)
            raise typer.Exit(1)

        owner, name = repo.split("/", 1)

        # Check if already tracked
        if is_repo_tracked(owner, name, cache_dir=cache_dir):
            typer.echo(f"{owner}/{name} is already tracked")
            return

        # Add to tracking
        save_tracked_repo(owner, name, cache_dir=cache_dir)
        typer.echo(f"Now tracking {owner}/{name}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def untrack_command(
    repo: str = typer.Argument(..., help="Repository to untrack (owner/name)"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Verbose output"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Remove a repository from continuous tracking.

    Examples:
      iceberg untrack facebook/react
    """
    setup_verbose_logging(verbose)

    try:
        cache_dir = resolve_cache_dir(cache_dir)

        if "/" not in repo:
            typer.echo("Error: Repository must be in owner/name format", err=True)
            raise typer.Exit(1)

        owner, name = repo.split("/", 1)

        # Check if tracked
        if not is_repo_tracked(owner, name, cache_dir=cache_dir):
            typer.echo(f"{owner}/{name} is not tracked")
            return

        # Remove from tracking
        remove_tracked_repo(owner, name, cache_dir=cache_dir)
        typer.echo(f"No longer tracking {owner}/{name}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def list_tracked_command(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Verbose output"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """List all tracked repositories.

    Examples:
      iceberg list-tracked
      iceberg list-tracked --json
    """
    setup_verbose_logging(verbose)

    try:
        cache_dir = resolve_cache_dir(cache_dir)

        tracked = load_tracked_repos(cache_dir=cache_dir)

        if json_output:
            typer.echo(json.dumps(tracked, indent=2))
        else:
            if not tracked:
                typer.echo("No repositories are being tracked")
            else:
                typer.echo(f"Tracking {len(tracked)} repositories:")
                for entry in tracked:
                    typer.echo(f"  - {entry['owner']}/{entry['repo']} (added {entry['added_at']})")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
