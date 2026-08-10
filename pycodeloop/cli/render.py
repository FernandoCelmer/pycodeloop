"""Render module"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text

console = Console()

_TOOL_ICONS = {
    "read_file": "📖",
    "write_file": "📝",
    "edit_file": "✏️",
    "delete_file": "🗑️",
    "list_dir": "📁",
    "glob": "🔎",
    "grep": "🔍",
    "bash": "💻",
    "web_fetch": "🌐",
    "http_request": "🔌",
    "git_status": "🌿",
    "git_diff": "🌿",
    "git_log": "🌿",
    "git_commit": "🌿",
    "env": "🧾",
    "todo": "✅",
    "read_skill": "🧠",
}


def tool_icon(name: str) -> str:
    return _TOOL_ICONS.get(name, "🔧")


def format_tokens(count: int) -> str:
    return f"{count / 1000:.1f}k" if count >= 1000 else str(count)


def format_args(args: dict) -> str:
    if len(args) == 1:
        (value,) = args.values()
        preview = str(value)
    else:
        preview = ", ".join(f"{key}={value}" for key, value in args.items())
    return preview if len(preview) <= 100 else preview[:100] + "…"


def format_tool_call(name: str, args: dict) -> str:
    """One clean, markup-safe line for a tool call — `bash` shows the
    real shell command with a `$` prompt instead of `command='...'`."""
    if name == "bash" and "command" in args:
        command = str(args["command"])
        command = command if len(command) <= 100 else command[:100] + "…"
        return f"💻 [bold white]$[/bold white] {escape(command)}"
    icon = tool_icon(name)
    preview = escape(format_args(args))
    return f"{icon} [bold white]{name}[/bold white] [dim]{preview}[/dim]"


class TurnBuffer:
    """Buffers streamed text, prints it as one Markdown block per turn
    instead of redrawing in place (which corrupts the active prompt)."""

    def __init__(self, console: Console) -> None:
        self._console = console
        self._text = ""

    def delta(self, chunk: str) -> None:
        self._text += chunk

    def flush(self) -> None:
        if self._text.strip():
            self._console.print(
                Panel(
                    Markdown(self._text),
                    border_style="grey50",
                    subtitle=(
                        "[bold white on grey30] CodeLoop [/bold white on grey30]"
                    ),
                    subtitle_align="right",
                )
            )
        self._text = ""


def styled_text(prefix_markup: str, plain: str, style: str = "") -> Text:
    """A self-contained `prefix_markup` (its own tags balanced) followed
    by `plain` appended as literal text, never parsed as markup — an
    arbitrary `[` in tool output/file content/user text can otherwise
    crash a Rich `Console`/Textual `Static` with a `MarkupError`."""
    text = Text.from_markup(prefix_markup)
    text.append(plain, style=style or None)
    return text


def render_preview(preview: str) -> Text:
    text = Text()
    for line in preview.splitlines(keepends=True):
        if line.startswith("+") and not line.startswith("+++"):
            text.append(line, style="bold white")
        elif line.startswith("-") and not line.startswith("---"):
            text.append(line, style="grey50")
        elif line.startswith("$"):
            text.append(line, style="bold white")
        else:
            text.append(line, style="dim")
    return text


def print_header(provider_name: str, model: str, hint: str) -> None:
    body = Text()
    body.append("CodeLoop", style="bold white")
    body.append(f"  {provider_name}", style="grey70")
    body.append(f" · {model}\n", style="grey70")
    body.append(f"{Path.cwd()}\n", style="dim")
    body.append(hint, style="dim")
    console.print(Panel(body, border_style="grey50"))
