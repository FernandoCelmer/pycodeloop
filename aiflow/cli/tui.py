"""Tui module"""

from __future__ import annotations

import os
import queue
import time

from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widgets import Header, Static, TextArea

from aiflow.abc.provider import Usage
from aiflow.cli.render import (
    format_tokens,
    format_tool_call,
    render_preview,
    tool_icon,
)
from aiflow.core.aiflow import AIFlow


class PromptArea(TextArea):
    """Multi-line prompt box. Enter submits; shift+enter/alt+enter/ctrl+j
    inserts a newline — pasted multi-line text (e.g. a traceback) goes in
    untouched since paste bypasses key bindings entirely. shift+enter only
    works in terminals with the extended keyboard protocol (Kitty, iTerm2,
    WezTerm, Ghostty); alt+enter and ctrl+j work everywhere. A trailing
    backslash before Enter also inserts a newline (the backslash is
    consumed) — a universal fallback that needs no terminal support at
    all, for terminals (plain Terminal.app, tmux, VS Code's integrated
    terminal) that report every modifier combination as plain Enter."""

    class Submitted(Message):
        def __init__(self, value: str) -> None:
            self.value = value
            super().__init__()

    async def _on_key(self, event) -> None:
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            line, column = self.cursor_location
            before_cursor = self.document.get_line(line)[:column]
            if before_cursor.endswith("\\"):
                self.action_delete_left()
                self.insert("\n")
            else:
                self.post_message(self.Submitted(self.text))
            return
        if event.key in ("shift+enter", "alt+enter", "ctrl+j"):
            event.prevent_default()
            event.stop()
            self.insert("\n")
            return
        await super()._on_key(event)


class AIFlowApp(App):
    """Full-screen chat UI. Textual owns the whole terminal, so there is
    no second stdin reader to race — the class of bug that broke the
    plain-terminal chat's live redraw doesn't apply here."""

    CSS = """
    #log {
        border: round grey;
        padding: 0 1;
        align-vertical: bottom;
    }
    PromptArea {
        border: round grey;
        dock: bottom;
        height: 6;
    }
    """
    BINDINGS = [("ctrl+c", "quit", "Quit")]
    ENABLE_COMMAND_PALETTE = False

    def __init__(self, flow: AIFlow, provider_name: str, model_name: str) -> None:
        super().__init__(ansi_color=True)
        self.flow = flow
        self.provider_name = provider_name
        self.model_name = model_name
        self._text_buffer = ""
        self._awaiting_confirm = False
        self._confirm_queue: queue.Queue = queue.Queue()
        self._stale_confirm_answer = False
        self._stale_expires_at = 0.0
        self._busy = False
        self._pending: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="log")
        yield PromptArea(placeholder="Type a message…", id="prompt")

    def on_mount(self) -> None:
        self.title = "AIFlow"
        self.sub_title = f"{self.provider_name}/{self.model_name}"
        self._log(
            Panel(
                f"[bold white]AIFlow[/bold white] ready\n"
                f"[grey70]{self.provider_name}[/grey70] · "
                f"[grey70]{self.model_name}[/grey70]\n"
                f"[dim]{os.getcwd()}[/dim]",
                border_style="grey50",
            )
        )
        self.query_one("#prompt", PromptArea).focus()

        self.flow.agent.on_request = self._on_request
        self.flow.agent.on_tool_call = self._on_tool_call
        self.flow.agent.on_tool_result = self._on_tool_result
        self.flow.agent.on_text_delta = self._on_text_delta
        self.flow.agent.on_usage = self._on_usage
        self.flow.agent.confirm = self._confirm

    def _log(self, renderable) -> None:
        log = self.query_one("#log", VerticalScroll)
        log.mount(Static(renderable))
        log.scroll_end(animate=False)

    def _handle_command(self, text: str) -> bool:
        """Handle a `/model`/`/reload` slash command. Returns True if
        `text` was a command (caller should not send it to the agent)."""
        if text == "/model":
            self._log(f"[dim]current model: {self.flow.agent.provider.model}[/dim]")
            return True

        if text.startswith("/model "):
            self.flow.agent.provider.model = text[len("/model ") :].strip()
            self.model_name = self.flow.agent.provider.model
            self.sub_title = f"{self.provider_name}/{self.model_name}"
            self._log(f"[dim]switched to model: {self.model_name}[/dim]")
            return True

        if text == "/reload":
            reload = getattr(self.flow.agent.provider, "reload", None)
            if reload is None:
                self._log(
                    "[dim]this provider wasn't loaded from a JSON "
                    "config, nothing to reload[/dim]"
                )
                return True
            reload()
            self.model_name = self.flow.agent.provider.model
            self.sub_title = f"{self.provider_name}/{self.model_name}"
            self._log(f"[dim]reloaded — model: {self.model_name}[/dim]")
            return True

        return False

    def on_prompt_area_submitted(self, event: PromptArea.Submitted) -> None:
        prompt = self.query_one("#prompt", PromptArea)
        text = event.value.strip()
        prompt.text = ""

        if self._awaiting_confirm:
            self._confirm_queue.put(text)
            return

        if not text:
            return
        if text in {"exit", "quit"}:
            self.exit()
            return
        if self._handle_command(text):
            return

        self._log(
            Panel(
                escape(text),
                border_style="bold white",
                subtitle="[bold black on white] You [/bold black on white]",
                subtitle_align="right",
            )
        )

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
        except Exception as exc:
            self.call_from_thread(self._log, f"[bold white]✗ Error:[/bold white] {exc}")
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
        self.call_from_thread(self._log, format_tool_call(name, args))

    def _on_tool_result(self, name: str, result: str, is_error: bool) -> None:
        preview = result if len(result) < 500 else result[:500] + "…"
        if result == "User declined to run this tool.":
            self.call_from_thread(self._log, "  [dim]⊘ skipped[/dim]")
        elif result.startswith("User declined and said: "):
            said = result[len("User declined and said: ") :]
            self.call_from_thread(
                self._log, f"  [bold white]↪ redirected:[/bold white] {said}"
            )
        elif is_error:
            self.call_from_thread(
                self._log, f"  [bold white]✗[/bold white] [dim]{preview}[/dim]"
            )
        else:
            self.call_from_thread(
                self._log, f"  [bold white]✓[/bold white] [dim]{preview}[/dim]"
            )

    def _on_text_delta(self, delta: str) -> None:
        self._text_buffer += delta

    def _on_usage(self, _turn: Usage, total: Usage, elapsed: float) -> None:
        if self._text_buffer.strip():
            self.call_from_thread(
                self._log,
                Panel(
                    Markdown(self._text_buffer),
                    border_style="grey50",
                    subtitle=("[bold white on grey30] AIFlow [/bold white on grey30]"),
                    subtitle_align="right",
                ),
            )
        self._text_buffer = ""
        tokens = (
            format_tokens(total.input_tokens)
            + " in / "
            + format_tokens(total.output_tokens)
            + " out"
        )
        self.call_from_thread(self._log, f"[dim]🤖 {tokens} · {elapsed:.1f}s[/dim]")

    def _show_confirm_prompt(self, name: str, preview: str) -> None:
        self._log(
            Panel(
                render_preview(preview),
                title=f"{tool_icon(name)} run {name}?",
                subtitle="[dim]Enter/y = run · n = skip[/dim]",
                border_style="grey50",
            )
        )

    CONFIRM_TIMEOUT = 3.0
    _STALE_ANSWER_GRACE = 10.0

    def _drain_stale_confirm_answer(self) -> None:
        """A confirm that timed out leaves the reader still waiting for
        that line — if it lands after we've already moved on to the
        *next* confirm, it would otherwise be misread as that prompt's
        answer. Discard it here instead, once, within a grace window."""
        if not self._stale_confirm_answer:
            return
        if time.monotonic() > self._stale_expires_at:
            self._stale_confirm_answer = False
            return
        try:
            self._confirm_queue.get_nowait()
        except queue.Empty:
            return
        self._stale_confirm_answer = False

    def _confirm(self, name: str, preview: str) -> bool | str:
        self._drain_stale_confirm_answer()
        self._awaiting_confirm = True
        self.call_from_thread(self._show_confirm_prompt, name, preview)
        try:
            answer = self._confirm_queue.get(timeout=self.CONFIRM_TIMEOUT)
        except queue.Empty:
            self._awaiting_confirm = False
            self._stale_confirm_answer = True
            self._stale_expires_at = time.monotonic() + self._STALE_ANSWER_GRACE
            self.call_from_thread(
                self._log,
                "[dim]⏱ no response — running automatically[/dim]",
            )
            return True
        self._awaiting_confirm = False
        text = answer.strip()
        lowered = text.lower()
        if lowered in {"", "y", "yes"}:
            return True
        if lowered in {"n", "no"}:
            return False
        return text
