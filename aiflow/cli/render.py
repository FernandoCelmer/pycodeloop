"""Render module"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
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
    "read_skill": "🧠",
}


def tool_icon(name: str) -> str:
    return _TOOL_ICONS.get(name, "🔧")


def format_tokens(count: int) -> str:
    return f"{count / 1000:.1f}k" if count >= 1000 else str(count)


def format_args(args: dict) -> str:
    preview = ", ".join(f"{key}={value!r}" for key, value in args.items())
    return preview if len(preview) <= 100 else preview[:100] + "…"


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
            self._console.print(Markdown(self._text))
        self._text = ""


def render_preview(preview: str) -> Text:
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


def print_header(provider_name: str, model: str, hint: str) -> None:
    body = Text()
    body.append("AIFlow", style="bold")
    body.append(f"  {provider_name}", style="cyan")
    body.append(f" · {model}\n", style="cyan")
    body.append(f"{Path.cwd()}\n", style="dim")
    body.append(hint, style="dim")
    console.print(Panel(body, border_style="green"))
