"""Status command - show project status and analysis age."""

import json
from datetime import datetime, timezone
from pathlib import Path

import typer

from iceberg.cache import list_all_repos, load_project_loc
from iceberg.commands.helpers import resolve_cache_dir
from iceberg.tracking import load_tracked_repos


def status_command(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show per-repo age details"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    cache_dir: Path | None = typer.Option(None, help="Cache directory path"),
) -> None:
    """Show project status: repos known, analyzed, exported, and analysis age.

    Examples:
      iceberg status
      iceberg status -v
      iceberg status --json
    """
    try:
        cache_dir = resolve_cache_dir(cache_dir)

        discovered = list_all_repos(cache_dir=cache_dir)
        tracked = load_tracked_repos(cache_dir=cache_dir)

        analyzed_count = 0
        with_deps = 0
        with_ai = 0
        age_buckets = {"< 1 day": 0, "1-7 days": 0, "7-30 days": 0, "> 30 days": 0}
        oldest_repo = None
        oldest_days = 0.0
        repo_ages: list[dict] = []

        projects_dir = cache_dir / "projects"
        if projects_dir.exists():
            for owner_dir in projects_dir.iterdir():
                if not owner_dir.is_dir():
                    continue
                for repo_dir in owner_dir.iterdir():
                    if not repo_dir.is_dir():
                        continue
                    head_file = repo_dir / "HEAD.json"
                    if head_file.exists():
                        analyzed_count += 1
                        try:
                            data = json.loads(head_file.read_text())
                            if "dependencies" in data and isinstance(data["dependencies"], dict):
                                with_deps += 1
                            if "ai_tools" in data and data["ai_tools"]:
                                with_ai += 1

                            cached_at = data.get("cached_at")
                            if cached_at:
                                cached_time = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
                                age = datetime.now(timezone.utc) - cached_time
                                days = age.total_seconds() / 86400

                                if days < 1:
                                    age_buckets["< 1 day"] += 1
                                elif days < 7:
                                    age_buckets["1-7 days"] += 1
                                elif days < 30:
                                    age_buckets["7-30 days"] += 1
                                else:
                                    age_buckets["> 30 days"] += 1

                                if days > oldest_days:
                                    oldest_days = days
                                    oldest_repo = f"{owner_dir.name}/{repo_dir.name}"

                                repo_ages.append({
                                    "repo": f"{owner_dir.name}/{repo_dir.name}",
                                    "days": days,
                                })
                        except (json.JSONDecodeError, ValueError, KeyError):
                            pass

        export_dir = cache_dir.parent / "spa" / "public"
        index_file = export_dir / "index.json"
        exported = index_file.exists()

        if json_output:
            output = {
                "discovered": len(discovered),
                "tracked": len(tracked),
                "analyzed": analyzed_count,
                "with_dependencies": with_deps,
                "with_ai_tools": with_ai,
                "age_buckets": age_buckets,
                "exported": exported,
            }
            if verbose:
                output["repo_ages"] = sorted(repo_ages, key=lambda x: x["days"], reverse=True)
            typer.echo(json.dumps(output, indent=2))
        else:
            typer.echo(f"Repositories discovered: {len(discovered)}")
            typer.echo(f"Repositories tracked: {len(tracked)}")
            typer.echo(f"Repositories analyzed: {analyzed_count}")
            typer.echo(f"  - With dependency analysis: {with_deps}")
            typer.echo(f"  - With AI tool detection: {with_ai}")
            typer.echo("\nAnalysis age distribution:")
            for bucket, count in age_buckets.items():
                typer.echo(f"  {bucket}: {count}")
            if oldest_repo:
                typer.echo(f"\nOldest analysis: {oldest_repo} ({oldest_days:.1f} days)")
            typer.echo(f"\nExported to SPA: {'Yes' if exported else 'No'}")

            if verbose and repo_ages:
                typer.echo("\nPer-repo analysis ages (oldest first):")
                for entry in sorted(repo_ages, key=lambda x: x["days"], reverse=True)[:20]:
                    typer.echo(f"  {entry['repo']}: {entry['days']:.1f} days")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
