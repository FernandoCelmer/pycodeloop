"""Search Tools"""

from __future__ import annotations

import re
from pathlib import Path

from pycodeloop.abc.tool import Tool, ToolResult
from pycodeloop.tools._limits import truncate
from pycodeloop.tools._workspace import (
    OutsideWorkspaceError,
    resolve_in_workspace,
)

_SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".ruff_cache",
}


def _is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return b"\0" in f.read(8192)
    except OSError:
        return True


class GrepTool(Tool):
    name = "grep"
    description = "Search for a regex pattern across files under a path."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string", "default": "."},
            "max_results": {"type": "integer", "default": 100},
        },
        "required": ["pattern"],
    }

    def __init__(self, workspace: bool = True) -> None:
        self._workspace = workspace

    def run(
        self, pattern: str, path: str = ".", max_results: int = 100
    ) -> ToolResult:
        try:
            root = resolve_in_workspace(path, enabled=self._workspace)
        except OutsideWorkspaceError as exc:
            return ToolResult(output=str(exc), is_error=True)

        try:
            regex = re.compile(pattern)
        except re.error as exc:
            return ToolResult(output=f"Invalid regex: {exc}", is_error=True)

        matches: list[str] = []
        for file_path in root.rglob("*"):
            if not file_path.is_file() or set(file_path.parts) & _SKIP_DIRS:
                continue
            if _is_binary(file_path):
                continue
            try:
                text = file_path.read_text(errors="ignore")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    matches.append(f"{file_path}:{lineno}: {line.strip()}")
                    if len(matches) >= max_results:
                        return ToolResult(output=truncate("\n".join(matches)))

        return ToolResult(
            output=truncate("\n".join(matches)) if matches else "No matches."
        )


class GlobTool(Tool):
    name = "glob"
    description = "Find files by glob pattern (e.g. '**/*.py')."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string", "default": "."},
            "max_results": {"type": "integer", "default": 100},
        },
        "required": ["pattern"],
    }

    def __init__(self, workspace: bool = True) -> None:
        self._workspace = workspace

    def run(
        self, pattern: str, path: str = ".", max_results: int = 100
    ) -> ToolResult:
        try:
            root = resolve_in_workspace(path, enabled=self._workspace)
        except OutsideWorkspaceError as exc:
            return ToolResult(output=str(exc), is_error=True)

        try:
            matches = [
                str(p)
                for p in root.glob(pattern)
                if not set(p.parts) & _SKIP_DIRS
            ]
        except (OSError, ValueError) as exc:
            return ToolResult(output=f"Invalid glob: {exc}", is_error=True)

        matches = sorted(matches)[:max_results]

        return ToolResult(
            output="\n".join(matches) if matches else "No matches."
        )
