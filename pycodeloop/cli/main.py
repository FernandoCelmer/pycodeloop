"""Main module"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from pycodeloop import __version__
from pycodeloop.cli.commands import chat, run
from pycodeloop.cli.flow import PROVIDER_HELP
from pycodeloop.cli.serve import serve

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

_cwd = str(Path.cwd())
if _cwd not in sys.path:
    sys.path.insert(0, _cwd)

app = typer.Typer(
    add_completion=False, help="CodeLoop — an agentic coding assistant."
)
app.command()(run)
app.command(name="chat")(chat)
app.command(name="serve")(serve)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"pycodeloop {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def default(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show the installed pycodeloop version and exit.",
    ),
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
    delegate: bool = typer.Option(
        False,
        "--delegate/--no-delegate",
        help=(
            "Expose a delegate tool that spawns read-only sub-agents for "
            "independent subtasks, run in parallel. Off by default."
        ),
    ),
    memory: bool = typer.Option(
        True,
        "--memory/--no-memory",
        help=(
            "Load .pycodeloop/memory.md into the system prompt and expose "
            "a remember tool so standing corrections persist across "
            "sessions. On by default."
        ),
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts for dangerous tools.",
    ),
) -> None:
    """Bare `pycodeloop` starts the chat; use `run`/`chat` for control."""
    if ctx.invoked_subcommand is None:
        chat(
            provider=provider,
            model=model,
            base_url=base_url,
            url=url,
            mcp=mcp,
            skills=skills,
            skills_refresh=skills_refresh,
            delegate=delegate,
            yes=yes,
        )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
