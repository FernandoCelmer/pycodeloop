"""Command chat module"""

from __future__ import annotations

import contextlib
import queue
import readline
import threading
from pathlib import Path

import typer
from rich.panel import Panel

from aiflow.cli.flow import PROVIDER_HELP, build_flow
from aiflow.cli.render import (
    console,
    print_header,
    render_preview,
    tool_icon,
)
from aiflow.core.aiflow import AIFlow
from aiflow.settings import Settings

_STOP = object()

_HISTORY_PATH = Path.home() / ".aiflow" / "history"


def _complete_path(text: str, state: int) -> str | None:
    try:
        matches = sorted(str(p) for p in Path().glob(f"{text}*"))
    except (OSError, ValueError):
        matches = []
    return matches[state] if state < len(matches) else None


def _init_readline() -> None:
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(FileNotFoundError):
        readline.read_history_file(_HISTORY_PATH)
    readline.set_history_length(1000)
    readline.set_completer(_complete_path)
    readline.parse_and_bind("tab: complete")


def _sync_prompt_after_prints() -> None:
    """Every `console.print` call while the background reader has an
    active `input()` prompt displayed corrupts readline's cursor
    tracking — not just the last one per turn. Wrap `console.print` so
    every single print re-syncs it, not only the one at end of turn."""
    original_print = console.print

    def wrapped(*args, **kwargs):
        original_print(*args, **kwargs)
        with contextlib.suppress(Exception):
            readline.redisplay()

    console.print = wrapped


def _read_stdin_into(prompt_queue: queue.Queue) -> None:
    """Background thread: the only thing that ever reads stdin. Chat
    messages and confirm-prompt answers both flow through this same
    queue, so there's no second stdin reader racing it."""
    _init_readline()
    while True:
        try:
            line = input("❯ ")
        except (EOFError, KeyboardInterrupt):
            prompt_queue.put(_STOP)
            return

        while line.endswith("\\"):
            try:
                more = input("… ")
            except (EOFError, KeyboardInterrupt):
                prompt_queue.put(_STOP)
                return
            line = line[:-1] + "\n" + more

        if line.strip():
            readline.add_history(line.replace("\n", " "))
            with contextlib.suppress(OSError):
                readline.write_history_file(_HISTORY_PATH)

        prompt_queue.put(line)


def _make_confirm(prompt_queue: queue.Queue, auto_approve: bool):
    """Confirm callback that answers from `prompt_queue` instead of its
    own stdin read — the background reader thread is always mid-`input()`
    waiting for the next line, so a separate blocking read would race it
    and silently steal the user's answer."""

    def confirm(name: str, preview: str) -> bool:
        if auto_approve:
            console.print("  [dim]running…[/dim]")
            return True

        console.print(
            Panel(
                render_preview(preview),
                title=f"{tool_icon(name)} {name}",
                border_style="yellow",
            )
        )
        while True:
            console.print(
                f"{Settings.QUESTION_ALERT} run '{name}'? [y/n] (y): ",
                end="",
            )
            answer = prompt_queue.get()
            if answer is _STOP:
                return False

            text = answer.strip().lower()
            if text in {"", "y", "yes"}:
                console.print("  [dim]running…[/dim]")
                return True
            if text:
                return False

    return confirm


def _chat_loop(flow: AIFlow, prompt_queue: queue.Queue) -> None:
    while True:
        try:
            item = prompt_queue.get()
        except KeyboardInterrupt:
            console.print("\nbye.")
            return

        if item is _STOP:
            console.print("\nbye.")
            return

        text = item.strip()
        if text in {"exit", "quit"}:
            console.print("bye.")
            return
        if not text:
            continue

        flow.run(text)
        console.print()


def chat(
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
    """Start an interactive AIFlow session in the current directory."""
    flow, provider_name, model_name = build_flow(
        provider,
        model,
        base_url,
        url,
        mcp,
        auto_approve=yes,
        skills=skills,
        skills_refresh=skills_refresh,
    )

    print_header(
        provider_name,
        model_name,
        "End a line with \\ to continue on the next line · Tab to "
        "complete paths · ↑/↓ for history · Ctrl+D/Ctrl+C or 'exit' "
        "to quit",
    )

    _sync_prompt_after_prints()

    prompt_queue: queue.Queue = queue.Queue()
    flow.agent.confirm = _make_confirm(prompt_queue, yes)
    threading.Thread(
        target=_read_stdin_into, args=(prompt_queue,), daemon=True
    ).start()
    _chat_loop(flow, prompt_queue)
