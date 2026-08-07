"""Tui module"""

from __future__ import annotations

import queue

from rich.markdown import Markdown
from rich.panel import Panel
from textual.app import App, ComposeResult
from textual.widgets import Header, Input, RichLog

from aiflow.abc.provider import Usage
from aiflow.cli.render import (
    format_args,
    format_tokens,
    render_preview,
    tool_icon,
)
from aiflow.core.aiflow import AIFlow


class AIFlowApp(App):
    """Full-screen chat UI. Textual owns the whole terminal, so there is
    no second stdin reader to race — the class of bug that broke the
    plain-terminal chat's live redraw doesn't apply here."""

    CSS = """
    RichLog {
        border: round grey;
        padding: 0 1;
    }
    Input {
        border: round grey;
        dock: bottom;
    }
    """
    BINDINGS = [("ctrl+c", "quit", "Quit")]
    ENABLE_COMMAND_PALETTE = False

    def __init__(
        self, flow: AIFlow, provider_name: str, model_name: str
    ) -> None:
        super().__init__(ansi_color=True)
        self.flow = flow
        self.provider_name = provider_name
        self.model_name = model_name
        self._text_buffer = ""
        self._awaiting_confirm = False
        self._confirm_queue: queue.Queue = queue.Queue()
        self._busy = False
        self._pending: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="log", wrap=True, markup=True, highlight=False)
        yield Input(placeholder="Type a message…", id="prompt")

    def on_mount(self) -> None:
        self.title = "AIFlow"
        self.sub_title = f"{self.provider_name}/{self.model_name}"
        self._log(
            f"[bold]AIFlow[/bold] ready — "
            f"{self.provider_name}/{self.model_name}"
        )
        self.query_one("#prompt", Input).focus()

        self.flow.agent.on_request = self._on_request
        self.flow.agent.on_tool_call = self._on_tool_call
        self.flow.agent.on_tool_result = self._on_tool_result
        self.flow.agent.on_text_delta = self._on_text_delta
        self.flow.agent.on_usage = self._on_usage
        self.flow.agent.confirm = self._confirm

    def _log(self, renderable) -> None:
        self.query_one("#log", RichLog).write(renderable)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = self.query_one("#prompt", Input)
        text = event.value.strip()
        prompt.value = ""

        if self._awaiting_confirm:
            self._confirm_queue.put(text)
            return

        if not text:
            return
        if text in {"exit", "quit"}:
            self.exit()
            return

        self._log(f"[bold blue]❯[/bold blue] {text}")

        if self._busy:
            self._pending.append(text)
            return

        self._start_turn(text)

    def _start_turn(self, text: str) -> None:
        self._busy = True
        self.run_worker(self._run_turn(text), thread=True)

    async def _run_turn(self, text: str) -> None:
        try:
            self.flow.run(text)
        finally:
            self.call_from_thread(self._finish_turn)

    def _finish_turn(self) -> None:
        self._busy = False
        if self._pending:
            self._start_turn(self._pending.pop(0))

    def _on_request(self, message_count: int, tool_count: int) -> None:
        self.call_from_thread(
            self._log,
            f"[dim]💭 {self.provider_name}/{self.model_name} — "
            f"{message_count} msg, {tool_count} tools…[/dim]",
        )

    def _on_tool_call(self, name: str, args: dict) -> None:
        icon = tool_icon(name)
        preview = format_args(args)
        self.call_from_thread(
            self._log,
            f"{icon} [bold cyan]{name}[/bold cyan] [dim]{preview}[/dim]",
        )

    def _on_tool_result(self, name: str, result: str, is_error: bool) -> None:
        preview = result if len(result) < 500 else result[:500] + "…"
        if result == "User declined to run this tool.":
            self.call_from_thread(self._log, "  [yellow]⊘ skipped[/yellow]")
        elif is_error:
            self.call_from_thread(
                self._log, f"  [red]✗[/red] [dim]{preview}[/dim]"
            )
        else:
            self.call_from_thread(
                self._log, f"  [green]✓[/green] [dim]{preview}[/dim]"
            )

    def _on_text_delta(self, delta: str) -> None:
        self._text_buffer += delta

    def _on_usage(self, _turn: Usage, total: Usage, elapsed: float) -> None:
        if self._text_buffer.strip():
            self.call_from_thread(self._log, Markdown(self._text_buffer))
        self._text_buffer = ""
        tokens = (
            format_tokens(total.input_tokens)
            + " in / "
            + format_tokens(total.output_tokens)
            + " out"
        )
        self.call_from_thread(
            self._log, f"[dim]🤖 {tokens} · {elapsed:.1f}s[/dim]"
        )

    def _show_confirm_prompt(self, name: str, preview: str) -> None:
        self._log(
            Panel(
                render_preview(preview),
                title=f"{tool_icon(name)} {name} — y/n?",
            )
        )

    def _confirm(self, name: str, preview: str) -> bool:
        self._awaiting_confirm = True
        self.call_from_thread(self._show_confirm_prompt, name, preview)
        answer = self._confirm_queue.get()
        self._awaiting_confirm = False
        return answer.strip().lower() in {"", "y", "yes"}
