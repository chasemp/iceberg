"""Discover command - discover repositories from multiple sources."""

from pathlib import Path

import typer

from iceberg.commands.helpers import resolve_cache_dir, setup_verbose_logging
from iceberg.discovery import run_discovery


def discover_command(
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Verbose output"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Discover repositories from trending, search, and ranking sources.

    Fetches repos from all discovery sources, deduplicates them,
    and saves metadata. Does NOT analyze repos.

    Examples:
      iceberg discover
      iceberg discover -v
    """
    setup_verbose_logging(verbose)

    try:
        cache_dir = resolve_cache_dir(cache_dir)

        def log(msg: str) -> None:
            if verbose:
                typer.echo(msg)

        results = run_discovery(cache_dir=cache_dir, verbose=bool(verbose), log=log)

        typer.echo("\nDiscovery complete:")
        typer.echo(f"  Total fetched:  {results['total_fetched']}")
        typer.echo(f"  Unique repos:   {results['unique_repos']}")
        typer.echo(f"  Sources saved:  {results['sources_saved']}")

        if verbose:
            typer.echo("\nBy source:")
            for source, count in sorted(results["sources"].items()):
                typer.echo(f"  {source}: {count}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
