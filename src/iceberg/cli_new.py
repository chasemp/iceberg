"""Iceberg CLI - Analyze code icebergs in open source projects.

This is the refactored CLI entry point that delegates to command modules.
"""

import typer

# Import command modules
from iceberg.commands.export_cmd import export_command
from iceberg.commands.fetch import fetch_command
from iceberg.commands.status import status_command

app = typer.Typer(
    name="iceberg",
    help="Analyze code icebergs in open source projects",
    no_args_is_help=True,
)

# Register commands
app.command(name="fetch")(fetch_command)
app.command(name="status")(status_command)
app.command(name="export")(export_command)


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
