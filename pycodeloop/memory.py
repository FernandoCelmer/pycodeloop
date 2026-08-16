"""Persistent project memory — notes the agent saves for itself so a
correction given in one session doesn't have to be repeated in the next."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pycodeloop.abc.tool import Tool, ToolResult

MEMORY_FILENAME = "memory.md"
_MEMORY_DIR = ".pycodeloop"


def memory_path(cwd: str | Path | None = None) -> Path:
    root = Path(cwd) if cwd is not None else Path.cwd()
    return root / _MEMORY_DIR / MEMORY_FILENAME


def load_memory(cwd: str | Path | None = None) -> str:
    try:
        return memory_path(cwd).read_text().strip()
    except OSError:
        return ""


def render_memory_prompt(content: str) -> str:
    if not content:
        return ""
    return (
        "The following notes were saved by you (or a previous session) in "
        "this project's memory file — standing corrections, preferences, "
        "and facts the user gave you that apply to every future session, "
        "not just one conversation. Follow them without being asked again:\n\n"
        f"{content}"
    )


class RememberTool(Tool):
    name = "remember"
    description = (
        "Save a short, durable note to this project's memory file "
        "(.pycodeloop/memory.md) — a correction, preference, or standing "
        "rule that should apply in every future session, not just this "
        "conversation. Call it whenever the user corrects your approach "
        "('don't do X', 'always do Y') or explicitly says to remember "
        "something. Don't save one-off task details or anything already "
        "obvious from the code."
    )
    parameters = {
        "type": "object",
        "properties": {
            "note": {
                "type": "string",
                "description": "One short, self-contained note.",
            },
        },
        "required": ["note"],
    }
    operation = "execute_high_risk"

    def __init__(self, cwd: str | Path | None = None) -> None:
        self._path = memory_path(cwd)

    def preview(self, note: str, **_) -> str:
        return f"Append to {self._path}:\n{note}"

    def run(self, note: str) -> ToolResult:
        note = note.strip()
        if not note:
            return ToolResult(
                output="Empty note, nothing saved.", is_error=True
            )

        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            with self._path.open("a") as f:
                f.write(f"- ({timestamp}) {note}\n")
        except OSError as exc:
            return ToolResult(
                output=f"Error writing memory: {exc}", is_error=True
            )

        return ToolResult(output=f"Saved to {self._path}")
