"""Backfill AI command - backfill AI tool marker detection."""

from pathlib import Path

import typer

from iceberg.ai_markers import backfill_ai_markers
from iceberg.commands.helpers import resolve_cache_dir, setup_verbose_logging


def backfill_ai_command(
    force: bool = typer.Option(False, "--force", help="Re-run detection even for repos that already have markers"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Verbose output"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Backfill AI tool marker detection for analyzed repos.

    Scans all analyzed repositories and runs AI marker detection
    for any that don't have ai_markers data yet.

    Use --force to re-run detection on all repos (e.g., after adding new markers).

    Examples:
      iceberg backfill-ai
      iceberg backfill-ai --force
      iceberg backfill-ai -v
    """
    setup_verbose_logging(verbose)

    try:
        cache_dir = resolve_cache_dir(cache_dir)

        typer.echo("Backfilling AI tool markers...")
        if force:
            typer.echo("(force mode: re-running all detections)")

        stats = backfill_ai_markers(cache_dir, force=force, verbose=bool(verbose))

        typer.echo("\nDone!")
        typer.echo(f"  Total repos: {stats['total']}")
        typer.echo(f"  Scanned: {stats['total'] - stats['skipped']}")
        typer.echo(f"  Skipped (already had markers): {stats['skipped']}")
        typer.echo(f"  AI tools detected: {stats['detected']}")
        if stats['errors'] > 0:
            typer.echo(f"  Errors: {stats['errors']}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
