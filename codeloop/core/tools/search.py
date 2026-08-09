"""Search Tools"""

from __future__ import annotations

import re
from pathlib import Path

from codeloop.abc.tool import Tool, ToolResult

_SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".ruff_cache",
}


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

    def run(self, pattern: str, path: str = ".", max_results: int = 100) -> ToolResult:
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            return ToolResult(output=f"Invalid regex: {exc}", is_error=True)

        matches: list[str] = []
        for file_path in Path(path).rglob("*"):
            if not file_path.is_file() or set(file_path.parts) & _SKIP_DIRS:
                continue
            try:
                text = file_path.read_text(errors="ignore")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    matches.append(f"{file_path}:{lineno}: {line.strip()}")
                    if len(matches) >= max_results:
                        return ToolResult(output="\n".join(matches))

        return ToolResult(output="\n".join(matches) if matches else "No matches.")


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

    def run(self, pattern: str, path: str = ".", max_results: int = 100) -> ToolResult:
        try:
            matches = [
                str(p)
                for p in Path(path).glob(pattern)
                if not set(p.parts) & _SKIP_DIRS
            ]
        except (OSError, ValueError) as exc:
            return ToolResult(output=f"Invalid glob: {exc}", is_error=True)

        matches = sorted(matches)[:max_results]

        return ToolResult(output="\n".join(matches) if matches else "No matches.")
