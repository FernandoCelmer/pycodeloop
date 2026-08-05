"""AIFlow CLI: an interactive coding agent in the terminal."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

from aiflow.abc.provider import Usage
from aiflow.core.aiflow import AIFlow
from aiflow.core.config import Config
from aiflow.core.mcp import MCPServer, load_mcp_tools
from aiflow.core.tools import DEFAULT_TOOLS
from aiflow.providers import get_provider
from aiflow.settings import Settings

app = typer.Typer(add_completion=False, help="AIFlow — an agentic coding assistant.")
console = Console()

_cwd = str(Path.cwd())
if _cwd not in sys.path:
    sys.path.insert(0, _cwd)


def _format_tokens(count: int) -> str:
    return f"{count / 1000:.1f}k" if count >= 1000 else str(count)


def _render_preview(preview: str) -> Text:
    text = Text()
    for line in preview.splitlines(keepends=True):
        if line.startswith("+") and not line.startswith("+++"):
            text.append(line, style="green")
        elif line.startswith("-") and not line.startswith("---"):
            text.append(line, style="red")
        elif line.startswith("$"):
            text.append(line, style="bold yellow")
        else:
            text.append(line, style="dim")
    return text


def _load_mcp_tools(specs: list[str] | None) -> list:
    tools = list(DEFAULT_TOOLS)
    for spec in specs or []:
        parts = shlex.split(spec)
        server = MCPServer(command=parts[0], args=parts[1:])
        console.print(f"{Settings.INFO_ALERT} connecting to MCP server '{spec}'")
        tools.extend(load_mcp_tools(server))
    return tools


def _build_flow(
    provider_name: str | None,
    model: str | None,
    base_url: str | None = None,
    mcp: list[str] | None = None,
    auto_approve: bool = False,
) -> AIFlow:
    provider_name = provider_name or Settings.PROVIDER
    model = model or Settings.MODEL
    is_local_or_custom = provider_name == "ollama" or ":" in provider_name

    if not Settings.API_KEY and not is_local_or_custom and provider_name == Settings.PROVIDER:
        console.print(
            f"{Settings.WARNING_ALERT} no API key found for provider "
            f"'{provider_name}'. Set the matching *_API_KEY env var."
        )

    provider_kwargs = {"model": model, "api_key": Settings.API_KEY}
    if base_url:
        provider_kwargs["base_url"] = base_url
    provider = get_provider(provider_name, **provider_kwargs)

    def on_tool_call(name: str, args: dict) -> None:
        console.print(f"\n[cyan]{Settings.STEP_ICON} {name}[/cyan] {args}")

    def on_tool_result(name: str, result: str) -> None:
        preview = result if len(result) < 500 else result[:500] + "…"
        console.print(f"[dim]{preview}[/dim]")

    def on_text_delta(delta: str) -> None:
        console.print(delta, end="")

    def on_usage(_turn: Usage, total: Usage) -> None:
        tokens = _format_tokens(total.input_tokens) + " in / " + _format_tokens(total.output_tokens) + " out"
        console.print(f"\n[dim]{Settings.ICON} {tokens}[/dim]")

    def confirm(name: str, preview: str) -> bool:
        if auto_approve:
            return True
        console.print(Panel(_render_preview(preview), title=name, border_style="yellow"))
        return Confirm.ask(f"{Settings.QUESTION_ALERT} run '{name}'?", default=True)

    config = Config(provider=provider, tools=_load_mcp_tools(mcp))
    flow = AIFlow(config=config)
    flow.agent.on_tool_call = on_tool_call
    flow.agent.on_tool_result = on_tool_result
    flow.agent.on_text_delta = on_text_delta
    flow.agent.confirm = confirm
    flow.agent.on_usage = on_usage
    return flow


_PROVIDER_HELP = "anthropic | openai | ollama | 'module.path:ClassName' for a custom Provider"


@app.command()
def run(
    prompt: str = typer.Argument(..., help="Task for AIFlow to carry out."),
    provider: str = typer.Option(None, help=_PROVIDER_HELP),
    model: str = typer.Option(None, help="Model name override."),
    base_url: str = typer.Option(None, help="Override the API endpoint (local/self-hosted servers)."),
    mcp: list[str] = typer.Option(
        None, help="MCP server as 'command arg1 arg2'; repeatable."
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation prompts for dangerous tools."
    ),
) -> None:
    """Run a single prompt to completion, non-interactively."""
    flow = _build_flow(provider, model, base_url, mcp, auto_approve=yes)
    flow.run(prompt)
    console.print()


@app.command()
def chat(
    provider: str = typer.Option(None, help=_PROVIDER_HELP),
    model: str = typer.Option(None, help="Model name override."),
    base_url: str = typer.Option(None, help="Override the API endpoint (local/self-hosted servers)."),
    mcp: list[str] = typer.Option(
        None, help="MCP server as 'command arg1 arg2'; repeatable."
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation prompts for dangerous tools."
    ),
) -> None:
    """Start an interactive AIFlow session in the current directory."""
    flow = _build_flow(provider, model, base_url, mcp, auto_approve=yes)

    console.print(Panel("AIFlow ready. Ctrl+D or 'exit' to quit.", style="bold green"))
    while True:
        try:
            prompt = console.input("[bold blue]> [/bold blue]")
        except (EOFError, KeyboardInterrupt):
            console.print("\nbye.")
            break
        if prompt.strip() in {"exit", "quit"}:
            break
        if not prompt.strip():
            continue

        flow.run(prompt)
        console.print()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
