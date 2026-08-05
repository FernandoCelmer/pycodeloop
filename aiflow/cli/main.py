"""AIFlow CLI: an interactive coding agent in the terminal."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from aiflow.core.aiflow import AIFlow
from aiflow.core.config import Config
from aiflow.providers import get_provider
from aiflow.settings import Settings

app = typer.Typer(add_completion=False, help="AIFlow — an agentic coding assistant.")
console = Console()


def _build_flow(provider_name: str | None, model: str | None) -> AIFlow:
    provider_name = provider_name or Settings.PROVIDER
    model = model or Settings.MODEL

    if not Settings.API_KEY and provider_name == Settings.PROVIDER:
        console.print(
            f"{Settings.WARNING_ALERT} no API key found for provider "
            f"'{provider_name}'. Set the matching *_API_KEY env var."
        )

    provider = get_provider(provider_name, model=model, api_key=Settings.API_KEY)

    def on_tool_call(name: str, args: dict) -> None:
        console.print(f"[cyan]{Settings.STEP_ICON} {name}[/cyan] {args}")

    def on_tool_result(name: str, result: str) -> None:
        preview = result if len(result) < 500 else result[:500] + "…"
        console.print(f"[dim]{preview}[/dim]")

    config = Config(provider=provider)
    flow = AIFlow(config=config)
    flow.agent.on_tool_call = on_tool_call
    flow.agent.on_tool_result = on_tool_result
    return flow


@app.command()
def run(
    prompt: str = typer.Argument(..., help="Task for AIFlow to carry out."),
    provider: str = typer.Option(None, help="anthropic | openai"),
    model: str = typer.Option(None, help="Model name override."),
) -> None:
    """Run a single prompt to completion, non-interactively."""
    flow = _build_flow(provider, model)
    reply = flow.run(prompt)
    console.print(Markdown(reply))


@app.command()
def chat(
    provider: str = typer.Option(None, help="anthropic | openai"),
    model: str = typer.Option(None, help="Model name override."),
) -> None:
    """Start an interactive AIFlow session in the current directory."""
    flow = _build_flow(provider, model)

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

        reply = flow.run(prompt)
        console.print(Markdown(reply))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
