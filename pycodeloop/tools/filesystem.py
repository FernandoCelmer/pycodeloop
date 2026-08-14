"""Filesystem Tools"""

from __future__ import annotations

import difflib
import hashlib
import re
from pathlib import Path

from pycodeloop.abc.tool import Tool, ToolResult
from pycodeloop.store.file_access_log import FileAccessLog, default_log
from pycodeloop.tools._limits import truncate

_HUNK_HEADER = re.compile(r"^@@ -?\d+(,\d+)? \+?\d+(,\d+)? @@", re.MULTILINE)
_DIFF_PREAMBLE = re.compile(r"^--- .+\n\+\+\+ .+$", re.MULTILINE)


def _diff(path: str, before: str, after: str) -> str:
    lines = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=path,
        tofile=path,
    )
    return "".join(lines) or "(no changes)"


def _looks_like_diff(text: str) -> bool:
    return bool(_HUNK_HEADER.search(text) or _DIFF_PREAMBLE.search(text))


class ReadFileTool(Tool):
    name = "read_file"
    description = (
        "Read a text file's contents, optionally a line range. If you "
        "already read the exact same path and range in this session and "
        "it hasn't changed on disk since, this returns a short notice "
        "instead of repeating the content, to save tokens — pass "
        "force=true to get the full content again (e.g. if it scrolled "
        "out of your context after compaction)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to read"},
            "offset": {
                "type": "integer",
                "description": "1-indexed start line",
            },
            "limit": {"type": "integer", "description": "Max lines to read"},
            "force": {
                "type": "boolean",
                "description": "Show full content even if unchanged since your last read.",
                "default": False,
            },
        },
        "required": ["path"],
    }

    def __init__(self, access_log: FileAccessLog | None = None) -> None:
        self._log = access_log or default_log

    def run(
        self,
        path: str,
        offset: int = 1,
        limit: int | None = None,
        force: bool = False,
    ) -> ToolResult:
        target = Path(path)

        try:
            lines = target.read_text().splitlines()
        except OSError as exc:
            return ToolResult(output=f"Error reading {path}: {exc}", is_error=True)

        start = max(offset - 1, 0)
        end = start + limit if limit else len(lines)
        numbered = [
            f"{i + start + 1}\t{line}" for i, line in enumerate(lines[start:end])
        ]
        content = "\n".join(numbered)
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        last = self._log.last_record(path)
        unchanged = (
            not force
            and last is not None
            and last.action == "read"
            and last.offset == offset
            and last.limit == limit
            and last.content_hash == content_hash
        )

        self._log.record(
            path,
            "read",
            content_hash=content_hash,
            size=len(content),
            offset=offset,
            limit=limit,
        )

        if unchanged:
            span = f" (lines {offset}-{end})" if limit else ""
            return ToolResult(
                output=f"(unchanged since you last read {path}{span} — pass "
                "force=true to see it again)"
            )

        return ToolResult(output=truncate(content))


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

    def __init__(self, access_log: FileAccessLog | None = None) -> None:
        self._log = access_log or default_log

    def preview(self, path: str, content: str, **_) -> str:
        if _looks_like_diff(content):
            return (
                "content looks like a unified diff (has a '@@ ... @@' hunk "
                "header or '---'/'+++' file headers), not the file's actual "
                "text. Pass the full literal file content instead."
            )

        target = Path(path)

        try:
            before = target.read_text()
        except OSError:
            before = ""
        return _diff(path, before, content)

    def run(self, path: str, content: str) -> ToolResult:
        if _looks_like_diff(content):
            return ToolResult(
                output=(
                    "content looks like a unified diff (has a '@@ ... @@' hunk "
                    "header or '---'/'+++' file headers), not the file's actual "
                    "text. Pass the full literal file content instead."
                ),
                is_error=True,
            )

        target = Path(path)

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        except OSError as exc:
            return ToolResult(output=f"Error writing {path}: {exc}", is_error=True)

        self._log.record(
            path,
            "write",
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            size=len(content),
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

    def __init__(self, access_log: FileAccessLog | None = None) -> None:
        self._log = access_log or default_log

    def _apply(
        self, path: str, old_string: str, new_string: str, replace_all: bool
    ) -> tuple[Path, str, str] | ToolResult:
        if _looks_like_diff(new_string):
            return ToolResult(
                output=(
                    "new_string looks like a unified diff (has a '@@ ... @@' "
                    "hunk header or '---'/'+++' file headers), not literal "
                    "replacement text. Pass the actual code to substitute in, "
                    "not a diff of it."
                ),
                is_error=True,
            )

        target = Path(path)

        try:
            text = target.read_text()
        except OSError as exc:
            return ToolResult(output=f"Error reading {path}: {exc}", is_error=True)

        count = text.count(old_string)

        if count == 0:
            return ToolResult(output=f"old_string not found in {path}", is_error=True)

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

        return target, text, new_text

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

        _target, before, after = result

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

        target, _before, after = result
        target.write_text(after)

        self._log.record(
            path,
            "edit",
            content_hash=hashlib.sha256(after.encode()).hexdigest(),
            size=len(after),
        )

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

    def __init__(self, access_log: FileAccessLog | None = None) -> None:
        self._log = access_log or default_log

    def preview(self, path: str, **_) -> str:
        target = Path(path)

        try:
            before = target.read_text()
        except OSError as exc:
            return f"Error reading {path}: {exc}"
        return _diff(path, before, "")

    def run(self, path: str) -> ToolResult:
        target = Path(path)

        try:
            target.unlink()
        except OSError as exc:
            return ToolResult(output=f"Error deleting {path}: {exc}", is_error=True)

        self._log.record(path, "delete")

        return ToolResult(output=f"Deleted {path}")


class ListDirTool(Tool):
    name = "list_dir"
    description = "List files and directories at a given path."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "default": "."}},
    }

    def run(self, path: str = ".") -> ToolResult:
        target = Path(path)

        try:
            entries = sorted(target.iterdir())
        except OSError as exc:
            return ToolResult(output=f"Error listing {path}: {exc}", is_error=True)

        lines = [f"{'d' if e.is_dir() else 'f'} {e.name}" for e in entries]

        return ToolResult(output="\n".join(lines))
