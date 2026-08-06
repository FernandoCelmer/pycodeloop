"""Flow module"""

from __future__ import annotations

import shlex

import typer
from rich.panel import Panel
from rich.prompt import Confirm

from aiflow.abc.provider import Usage
from aiflow.cli.render import (
    TurnBuffer,
    console,
    format_args,
    format_tokens,
    render_preview,
    tool_icon,
)
from aiflow.core.aiflow import AIFlow
from aiflow.core.config import Config
from aiflow.core.mcp import MCPServer, load_mcp_tools
from aiflow.core.tools import DEFAULT_TOOLS
from aiflow.providers import get_provider
from aiflow.settings import Settings

PROVIDER_HELP = (
    "anthropic | openai | ollama | generic | "
    "'module.path:ClassName' for a custom Provider"
)


def _load_mcp_tools(specs: list[str] | None) -> list:
    tools = list(DEFAULT_TOOLS)
    for spec in specs or []:
        parts = shlex.split(spec)
        server = MCPServer(command=parts[0], args=parts[1:])
        console.print(
            f"{Settings.INFO_ALERT} connecting to MCP server '{spec}'"
        )
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
) -> tuple[AIFlow, str, str]:
    provider_name = provider_name or Settings.PROVIDER
    model = model or Settings.MODEL
    is_local_or_custom = (
        provider_name in {"ollama", "generic"} or ":" in provider_name
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
            console.print(
                f"{Settings.ERROR_ALERT} --provider generic requires --url"
            )
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
        icon = tool_icon(name)
        preview = format_args(args)
        console.print(
            f"\n{icon} [bold cyan]{name}[/bold cyan] [dim]{preview}[/dim]"
        )

    def on_tool_result(name: str, result: str, is_error: bool) -> None:
        preview = result if len(result) < 500 else result[:500] + "…"
        if result == "User declined to run this tool.":
            console.print("  [yellow]⊘ skipped[/yellow]")
        elif is_error:
            console.print(f"  [red]✗[/red] [dim]{preview}[/dim]")
        else:
            console.print(f"  [green]✓[/green] [dim]{preview}[/dim]")

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
        approved = Confirm.ask(
            f"{Settings.QUESTION_ALERT} run '{name}'?", default=True
        )
        if approved:
            console.print("  [dim]running…[/dim]")
        return approved

    config = Config(
        provider=provider,
        tools=_load_mcp_tools(mcp),
        skills=skills,
        skills_refresh=skills_refresh,
    )
    if config.skills:
        console.print(
            f"{Settings.INFO_ALERT} loaded {len(config.skills)} skill(s)"
        )

    flow = AIFlow(config=config)
    flow.agent.on_request = on_request
    flow.agent.on_tool_call = on_tool_call
    flow.agent.on_tool_result = on_tool_result
    flow.agent.on_text_delta = on_text_delta
    flow.agent.confirm = confirm
    flow.agent.on_usage = on_usage
    return flow, provider_name, model
