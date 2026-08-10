"""Flow module"""

from __future__ import annotations

import queue
import shlex
import threading
import uuid
from pathlib import Path

import typer
from rich.panel import Panel

from codeloop.abc.provider import Usage
from codeloop.cli.render import (
    TurnBuffer,
    console,
    format_tokens,
    format_tool_call,
    render_preview,
    tool_icon,
)
from codeloop.core.codeloop import CodeLoop
from codeloop.core.config import Config
from codeloop.core.mcp import MCPServer, MCPServerRegistry, load_mcp_tools
from codeloop.core.persistence.local_config import default_store
from codeloop.core.tools import DEFAULT_TOOLS
from codeloop.providers import get_provider
from codeloop.settings import Settings

PROVIDER_HELP = (
    "anthropic | openai | ollama | generic | path/to/config.json | "
    "'module.path:ClassName' for a custom Provider"
)

_CONFIRM_TIMEOUT = 3.0
_EOF = object()
_SESSION_IDS_SECTION = "session_ids"


def default_session_key() -> str:
    """A stable UUID per working directory, so `codeloop` resumes the
    same saved session when run again from the same project — the
    mapping (cwd -> id) lives in `~/.codeloop/config.json`, and the
    session's own `cwd` column is what stays human-readable."""
    cwd = str(Path.cwd())
    mapping = default_store.get_section(_SESSION_IDS_SECTION)

    session_id = mapping.get(cwd)
    if session_id is None:
        session_id = str(uuid.uuid4())
        mapping[cwd] = session_id
        default_store.set_section(_SESSION_IDS_SECTION, mapping)

    return session_id


def _load_mcp_tools(specs: list[str] | None) -> list:
    tools = list(DEFAULT_TOOLS)

    for spec in specs or []:
        if spec.startswith("saved:"):
            name = spec[len("saved:") :]
            server = MCPServerRegistry().load(name)

            if server is None:
                console.print(
                    f"{Settings.ERROR_ALERT} no saved MCP server named '{name}'"
                )
                raise typer.Exit(code=1)
        else:
            parts = shlex.split(spec)
            server = MCPServer(command=parts[0], args=parts[1:])

        console.print(f"{Settings.INFO_ALERT} connecting to MCP server '{spec}'")
        tools.extend(load_mcp_tools(server))

    return tools


def build_flow(
    provider_name: str | None,
    model: str | None,
    base_url: str | None = None,
    url: str | None = None,
    mcp: list[str] | None = None,
    auto_approve: bool = False,
    skills: bool = False,
    skills_refresh: bool = False,
) -> tuple[CodeLoop, str, str]:
    provider_name = provider_name or Settings.PROVIDER
    model = model or Settings.MODEL
    is_local_or_custom = (
        provider_name in {"ollama", "generic"}
        or ":" in provider_name
        or provider_name.endswith(".json")
    )

    if (
        not Settings.API_KEY
        and not is_local_or_custom
        and provider_name == Settings.PROVIDER
    ):
        console.print(
            f"{Settings.WARNING_ALERT} no API key found for provider "
            f"'{provider_name}'. Set the matching *_API_KEY env var."
        )

    provider_kwargs = {"model": model, "api_key": Settings.API_KEY}
    if provider_name == "generic":
        if not url:
            console.print(f"{Settings.ERROR_ALERT} --provider generic requires --url")
            raise typer.Exit(code=1)
        provider_kwargs["url"] = url
    elif base_url:
        provider_kwargs["base_url"] = base_url
    provider = get_provider(provider_name, **provider_kwargs)

    buffer = TurnBuffer(console)

    def on_request(message_count: int, tool_count: int) -> None:
        console.print(
            f"[dim]💭 {provider_name}/{model} — {message_count} msg in "
            f"context, {tool_count} tools available…[/dim]"
        )

    def on_tool_call(name: str, args: dict) -> None:
        buffer.flush()
        console.print(f"\n{format_tool_call(name, args)}")

    def on_tool_result(name: str, result: str, is_error: bool) -> None:
        preview = result if len(result) < 500 else result[:500] + "…"
        if result == "User declined to run this tool.":
            console.print("  [dim]⊘ skipped[/dim]")
        elif result.startswith("User declined and said: "):
            said = result[len("User declined and said: ") :]
            console.print(f"  [bold white]↪ redirected:[/bold white] {said}")
        elif is_error:
            console.print(f"  [bold white]✗[/bold white] [dim]{preview}[/dim]")
        else:
            console.print(f"  [bold white]✓[/bold white] [dim]{preview}[/dim]")

    def on_text_delta(delta: str) -> None:
        buffer.delta(delta)

    def on_usage(_turn: Usage, total: Usage, elapsed: float) -> None:
        buffer.flush()
        tokens = (
            format_tokens(total.input_tokens)
            + " in / "
            + format_tokens(total.output_tokens)
            + " out"
        )
        console.print(f"[dim]{Settings.ICON} {tokens} · {elapsed:.1f}s[/dim]")

    answer_queue: queue.Queue = queue.Queue()
    reader_started = False

    def ensure_reader() -> None:
        """One persistent stdin reader for the whole `run` invocation —
        a fresh thread per confirm() call would leave orphaned threads
        racing each other for stdin after every timeout."""
        nonlocal reader_started
        if reader_started:
            return
        reader_started = True

        def read_loop() -> None:
            while True:
                try:
                    answer_queue.put(input())
                except (EOFError, KeyboardInterrupt):
                    # Distinct from a bare Enter (which legitimately means
                    # "yes") — stdin being closed/unavailable must default
                    # to declining, not silently approving dangerous tools.
                    answer_queue.put(_EOF)
                    return

        threading.Thread(target=read_loop, daemon=True).start()

    def confirm(name: str, preview: str) -> bool | str:
        if auto_approve:
            console.print("  [dim]running…[/dim]")
            return True

        console.print(
            Panel(
                render_preview(preview),
                title=f"{tool_icon(name)} {name}",
                border_style="grey50",
            )
        )
        console.print(f"{Settings.QUESTION_ALERT} run '{name}'? [y/n] (y): ", end="")

        ensure_reader()
        try:
            answer = answer_queue.get(timeout=_CONFIRM_TIMEOUT)
        except queue.Empty:
            console.print("\n  [dim]⏱ no response — running automatically[/dim]")
            return True

        if answer is _EOF:
            console.print("\n  [dim]⊘ stdin closed — declining[/dim]")
            return False

        text = answer.strip()
        lowered = text.lower()
        if lowered in {"", "y", "yes"}:
            console.print("  [dim]running…[/dim]")
            return True
        if lowered in {"n", "no"}:
            return False
        return text

    config = Config(
        provider=provider,
        tools=_load_mcp_tools(mcp),
        skills=skills,
        skills_refresh=skills_refresh,
    )
    if config.skills:
        console.print(f"{Settings.INFO_ALERT} loaded {len(config.skills)} skill(s)")

    flow = CodeLoop(config=config)
    flow.agent.on_request = on_request
    flow.agent.on_tool_call = on_tool_call
    flow.agent.on_tool_result = on_tool_result
    flow.agent.on_text_delta = on_text_delta
    flow.agent.confirm = confirm
    flow.agent.on_usage = on_usage
    return flow, provider_name, model
