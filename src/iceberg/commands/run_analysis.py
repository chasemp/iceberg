"""Run analysis command - batch analysis of stale repositories."""

import time
from pathlib import Path

import typer

from iceberg.cache import list_all_repos
from iceberg.calculator import analyze_repository
from iceberg.commands.helpers import resolve_cache_dir, setup_verbose_logging
from iceberg.staleness import (
    determine_tier,
    is_stale,
    load_staleness_config,
    prioritize_repos,
)


def run_analysis_command(
    batch_size: int = typer.Option(25, "--batch-size", help="Max repos to analyze per run"),
    force: bool = typer.Option(False, "--force", help="Force re-analysis regardless of staleness"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Verbose output"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Analyze repos that are new or have stale analysis data.

    Checks all discovered repos against staleness thresholds from
    config/staleness.json. Analyzes up to --batch-size repos per run.

    Examples:
      iceberg run-analysis
      iceberg run-analysis -v
      iceberg run-analysis --batch-size 50
      iceberg run-analysis --force --batch-size 10 -v
    """
    setup_verbose_logging(verbose)

    try:
        cache_dir = resolve_cache_dir(cache_dir)
        config = load_staleness_config()

        typer.echo("Loading discovered repositories...")
        all_repos = list_all_repos(cache_dir=cache_dir)
        typer.echo(f"Found {len(all_repos)} repos in cache")

        if force:
            typer.echo("Mode: FORCE (re-analyzing all repos)")

        candidates = []
        skipped = 0
        for repo_meta in all_repos:
            owner = repo_meta["owner"]
            name = repo_meta["name"]

            stale, reason = is_stale(owner, name, cache_dir=cache_dir, config=config, force=force)
            if stale:
                tier = determine_tier(owner, name, cache_dir=cache_dir, config=config)
                candidates.append({"owner": owner, "name": name, "tier": tier, "reason": reason})
            else:
                skipped += 1
                if verbose:
                    typer.echo(f"  skip {owner}/{name} - {reason}")

        candidates = prioritize_repos(candidates)
        to_analyze = candidates[:batch_size]

        typer.echo(f"\nStale: {len(candidates)}, Skipped: {skipped}")
        typer.echo(f"Analyzing: {len(to_analyze)} (batch size: {batch_size})\n")

        analyzed = 0
        errors = 0
        pause_every = config.get("batch_pause_every_n", 10)
        pause_seconds = config.get("batch_pause_seconds", 2)

        for i, candidate in enumerate(to_analyze):
            owner = candidate["owner"]
            name = candidate["name"]
            tier = candidate["tier"]
            reason = candidate["reason"]

            typer.echo(f"[{i+1}/{len(to_analyze)}] {owner}/{name} ({tier}) - {reason}")

            try:
                result = analyze_repository(
                    owner=owner,
                    repo=name,
                    cache_dir=cache_dir,
                    verbose=bool(verbose),
                    force=force,
                )

                if result:
                    project_loc = result.get("project_loc") or result.get("loc", 0)
                    typer.echo(f"  Analyzed: {project_loc:,} LoC")
                    if "total_loc" in result:
                        typer.echo(f"  Dependencies: {result['total_loc']:,} LoC")
                    analyzed += 1
                else:
                    typer.echo("  Failed to analyze")
                    errors += 1

            except Exception as e:
                typer.echo(f"  Error: {e}")
                errors += 1

            if pause_every and (i + 1) % pause_every == 0 and i + 1 < len(to_analyze):
                time.sleep(pause_seconds)

        typer.echo("\nAnalysis complete:")
        typer.echo(f"  Analyzed:   {analyzed}")
        typer.echo(f"  Errors:     {errors}")
        typer.echo(f"  Skipped:    {skipped}")
        typer.echo(f"  Remaining:  {max(0, len(candidates) - batch_size)}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
