"""Export command - export data to SPA format."""

import json
from pathlib import Path

import typer

from iceberg.commands.helpers import resolve_cache_dir
from iceberg.export import export_all


def export_command(
    output_dir: Path | None = typer.Option(None, help="Output directory (default: spa/public)"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Export repository data to SPA-friendly JSON format.

    Examples:
      iceberg export
      iceberg export --output-dir ./my-spa/data
    """
    try:
        cache_dir = resolve_cache_dir(cache_dir)

        if output_dir is None:
            output_dir = cache_dir.parent / "spa" / "public"

        results = export_all(output_dir, cache_dir=cache_dir)

        typer.echo("Export complete:")
        typer.echo(f"  Discovery index: {results['discovery_index']['dimensions_exported']} dimensions")
        typer.echo(f"  Repository details: {results['repository_details']['repos_exported']} repos")
        typer.echo(f"  Output directory: {output_dir}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
