"""Main module"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from pycodeloop.cli.commands import run, tui
from pycodeloop.cli.flow import PROVIDER_HELP

sys.stdout.reconfigure(line_buffering=True)

_cwd = str(Path.cwd())
if _cwd not in sys.path:
    sys.path.insert(0, _cwd)

app = typer.Typer(add_completion=False, help="CodeLoop — an agentic coding assistant.")
app.command()(run)
app.command(name="tui")(tui)


@app.callback(invoke_without_command=True)
def default(
    ctx: typer.Context,
    provider: str = typer.Option(None, help=PROVIDER_HELP),
    model: str = typer.Option(None, help="Model name override."),
    base_url: str = typer.Option(
        None, help="Override the API endpoint (local/self-hosted servers)."
    ),
    url: str = typer.Option(
        None, help="Endpoint URL, required for --provider generic."
    ),
    mcp: list[str] = typer.Option(
        None, help="MCP server as 'command arg1 arg2'; repeatable."
    ),
    skills: bool = typer.Option(
        True,
        "--skills/--no-skills",
        help=(
            "Discover Claude/Cursor/AGENTS.md skills and expose a "
            "read_skill tool. On by default."
        ),
    ),
    skills_refresh: bool = typer.Option(
        False, "--skills-refresh", help="Bypass the skills cache and rescan."
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts for dangerous tools.",
    ),
) -> None:
    """Bare `pycodeloop` starts the TUI; use `run`/`tui` for control."""
    if ctx.invoked_subcommand is None:
        tui(
            provider=provider,
            model=model,
            base_url=base_url,
            url=url,
            mcp=mcp,
            skills=skills,
            skills_refresh=skills_refresh,
            yes=yes,
        )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
