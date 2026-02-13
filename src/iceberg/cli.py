"""CLI entry point for Iceberg - imports and registers command modules."""

import typer

from iceberg.commands.analyze import analyze_command
from iceberg.commands.backfill_ai import backfill_ai_command
from iceberg.commands.discover import discover_command
from iceberg.commands.export_cmd import export_command
from iceberg.commands.fetch import fetch_command
from iceberg.commands.run_analysis import run_analysis_command
from iceberg.commands.status import status_command
from iceberg.commands.track import list_tracked_command, track_command, untrack_command

app = typer.Typer()

# Register all commands
app.command(name="fetch")(fetch_command)
app.command(name="analyze")(analyze_command)
app.command(name="track")(track_command)
app.command(name="untrack")(untrack_command)
app.command(name="list-tracked")(list_tracked_command)
app.command(name="backfill-ai")(backfill_ai_command)
app.command(name="discover")(discover_command)
app.command(name="run-analysis")(run_analysis_command)
app.command(name="export")(export_command)
app.command(name="status")(status_command)


if __name__ == "__main__":
    app()
