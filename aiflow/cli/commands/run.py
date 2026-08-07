"""Command run module"""

from __future__ import annotations

import typer

from aiflow.cli.flow import PROVIDER_HELP, build_flow
from aiflow.cli.render import console


def run(
    prompt: str = typer.Argument(..., help="Task for AIFlow to carry out."),
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
    """Run a single prompt to completion, non-interactively."""
    flow, _provider_name, _model = build_flow(
        provider,
        model,
        base_url,
        url,
        mcp,
        auto_approve=yes,
        skills=skills,
        skills_refresh=skills_refresh,
    )
    flow.run(prompt)
    console.print()
