"""Filesystem Tools"""

from __future__ import annotations

import difflib
from pathlib import Path

from aiflow.abc.tool import Tool, ToolResult


def _diff(path: str, before: str, after: str) -> str:
    lines = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=path,
        tofile=path,
    )
    return "".join(lines) or "(no changes)"


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read a text file's contents, optionally a line range."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to read"},
            "offset": {
                "type": "integer",
                "description": "1-indexed start line",
            },
            "limit": {"type": "integer", "description": "Max lines to read"},
        },
        "required": ["path"],
    }

    def run(
        self, path: str, offset: int = 1, limit: int | None = None
    ) -> ToolResult:
        try:
            lines = Path(path).read_text().splitlines()
        except OSError as exc:
            return ToolResult(
                output=f"Error reading {path}: {exc}", is_error=True
            )

        start = max(offset - 1, 0)
        end = start + limit if limit else len(lines)
        numbered = [
            f"{i + start + 1}\t{line}"
            for i, line in enumerate(lines[start:end])
        ]
        return ToolResult(output="\n".join(numbered))


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write content to a file, creating or overwriting it."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }
    dangerous = True

    def preview(self, path: str, content: str, **_) -> str:
        try:
            before = Path(path).read_text()
        except OSError:
            before = ""
        return _diff(path, before, content)

    def run(self, path: str, content: str) -> ToolResult:
        try:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        except OSError as exc:
            return ToolResult(
                output=f"Error writing {path}: {exc}", is_error=True
            )
        return ToolResult(output=f"Wrote {len(content)} bytes to {path}")


class EditFileTool(Tool):
    name = "edit_file"
    description = "Replace an exact substring in a file with a new one."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_string": {"type": "string"},
            "new_string": {"type": "string"},
            "replace_all": {"type": "boolean", "default": False},
        },
        "required": ["path", "old_string", "new_string"],
    }
    dangerous = True

    def _apply(
        self, path: str, old_string: str, new_string: str, replace_all: bool
    ) -> tuple[str, str] | ToolResult:
        try:
            text = Path(path).read_text()
        except OSError as exc:
            return ToolResult(
                output=f"Error reading {path}: {exc}", is_error=True
            )

        count = text.count(old_string)
        if count == 0:
            return ToolResult(
                output=f"old_string not found in {path}", is_error=True
            )
        if count > 1 and not replace_all:
            return ToolResult(
                output=(
                    f"old_string is not unique in {path} "
                    f"({count} matches); pass replace_all=true or give "
                    "more context"
                ),
                is_error=True,
            )

        new_text = (
            text.replace(old_string, new_string)
            if replace_all
            else text.replace(old_string, new_string, 1)
        )
        return text, new_text

    def preview(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
        **_,
    ) -> str:
        result = self._apply(path, old_string, new_string, replace_all)
        if isinstance(result, ToolResult):
            return result.output
        before, after = result
        return _diff(path, before, after)

    def run(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> ToolResult:
        result = self._apply(path, old_string, new_string, replace_all)
        if isinstance(result, ToolResult):
            return result
        _before, after = result
        Path(path).write_text(after)
        return ToolResult(output=f"Edited {path}")


class DeleteFileTool(Tool):
    name = "delete_file"
    description = "Delete a file."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }
    dangerous = True

    def preview(self, path: str, **_) -> str:
        try:
            before = Path(path).read_text()
        except OSError as exc:
            return f"Error reading {path}: {exc}"
        return _diff(path, before, "")

    def run(self, path: str) -> ToolResult:
        try:
            Path(path).unlink()
        except OSError as exc:
            return ToolResult(
                output=f"Error deleting {path}: {exc}", is_error=True
            )
        return ToolResult(output=f"Deleted {path}")


class ListDirTool(Tool):
    name = "list_dir"
    description = "List files and directories at a given path."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "default": "."}},
    }

    def run(self, path: str = ".") -> ToolResult:
        try:
            entries = sorted(Path(path).iterdir())
        except OSError as exc:
            return ToolResult(
                output=f"Error listing {path}: {exc}", is_error=True
            )
        lines = [f"{'d' if e.is_dir() else 'f'} {e.name}" for e in entries]
        return ToolResult(output="\n".join(lines))
