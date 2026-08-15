"""Command run module"""

from __future__ import annotations

import json
import subprocess
import sys

import typer

from pycodeloop.cli.commands.run_result import (
    RunResult,
    exit_code_for,
    files_modified_from,
)
from pycodeloop.cli.flow import PROVIDER_HELP, build_flow, default_session_key
from pycodeloop.cli.render import console
from pycodeloop.store.file_access_log import default_log


def run(
    prompt: str = typer.Argument(..., help="Task for CodeLoop to carry out."),
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
    workspace: bool = typer.Option(
        True,
        "--workspace/--no-workspace",
        help=(
            "Jail read_file/write_file/edit_file/delete_file/grep/glob to "
            "the working directory. Does NOT cover bash/git, which run "
            "arbitrary shell commands. On by default."
        ),
    ),
    ci: bool = typer.Option(
        False,
        "--ci",
        help=(
            "CI mode: emit non-zero exit codes on failure (error, max "
            "turns, regression, or budget) and send human-readable logs "
            "to stderr so structured output stays on stdout."
        ),
    ),
    output: str = typer.Option(
        "text",
        "--output",
        help="Output format for the run result: 'text' (default) or 'json'.",
    ),
    check_cmd: str = typer.Option(
        None,
        "--check",
        "--check-cmd",
        help=(
            "Shell command run after the agent finishes; a non-zero exit "
            "marks the run as a regression (exit code 2 in --ci)."
        ),
    ),
    max_tokens: int = typer.Option(
        None,
        "--max-tokens",
        help=(
            "Token budget for the run; exceeding it fails the run with "
            "exit code 3 in --ci (status 'budget')."
        ),
    ),
) -> None:
    """Run a single prompt to completion, non-interactively."""
    json_mode = output == "json"
    console_file = console.file
    if ci or json_mode:
        console.file = sys.stderr

    session_key = default_session_key()
    flow, _, _ = build_flow(
        provider,
        model,
        base_url,
        url,
        mcp,
        auto_approve=yes,
        skills=skills,
        skills_refresh=skills_refresh,
        delegation=delegate,
        memory=memory,
        workspace=workspace,
    )

    messages_before = len(flow.session.messages)
    usage_before = flow.agent.usage

    error: Exception | None = None
    try:
        result_text = flow.run(prompt, session_key=session_key)
        reason = flow.agent.last_run_reason
    except Exception as exc:
        error = exc

    if error is not None:
        result = RunResult(status="error", text=str(error))
        _emit(result, json_mode)
        console.file = console_file
        if ci:
            raise typer.Exit(code=exit_code_for(result))
        return

    usage_after = flow.agent.usage
    input_tokens = usage_after.input_tokens - usage_before.input_tokens
    output_tokens = usage_after.output_tokens - usage_before.output_tokens

    added = flow.session.messages[messages_before:]
    turns = sum(1 for message in added if message.role == "assistant")

    files_modified = files_modified_from(default_log.history(session_key))

    regression = False
    if check_cmd:
        check = subprocess.run(
            check_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        regression = check.returncode != 0
        if regression:
            console.print(
                f"[dim]✗ regression — '{check_cmd}' exited "
                f"{check.returncode}[/dim]"
            )
            if check.stdout:
                console.print(check.stdout)

    status_by_reason = {
        "done": "success",
        "max_turns": "max_turns",
        "cancelled": "cancelled",
    }
    status = status_by_reason.get(reason or "done", "success")

    total_tokens = input_tokens + output_tokens
    if max_tokens is not None and total_tokens > max_tokens:
        status = "budget"

    result = RunResult(
        status=status,
        turns=turns,
        tokens={"input": input_tokens, "output": output_tokens},
        cost_usd=None,
        regression=regression,
        files_modified=files_modified,
        text=result_text,
    )

    _emit(result, json_mode)
    console.print()
    console.file = console_file

    if ci:
        raise typer.Exit(code=exit_code_for(result))


def _emit(result: RunResult, json_mode: bool) -> None:
    if json_mode:
        typer.echo(json.dumps(result.to_dict(), indent=2))
    elif result.status != "success":
        label = {
            "error": "error",
            "max_turns": "max turns reached",
            "cancelled": "cancelled",
            "budget": "budget exceeded",
        }.get(result.status, result.status)
        console.print(f"[bold white]✗ run failed:[/bold white] {label}")
