"""Bash Tool"""

from __future__ import annotations

import subprocess

from pycodeloop.abc.tool import Tool, ToolResult
from pycodeloop.core.errors import classify_error
from pycodeloop.tools._limits import truncate


class BashTool(Tool):
    name = "bash"
    description = (
        "Run a shell command and return its stdout/stderr. Not limited to "
        "the workspace root — unlike read_file/write_file/grep/etc, this "
        "runs an arbitrary command with full filesystem access, so use it "
        "for paths outside the project only when the user actually asked "
        "for that."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "integer", "default": 120},
        },
        "required": ["command"],
    }
    dangerous = True

    def preview(self, command: str, **_) -> str:
        return f"$ {command}"

    def run(self, command: str, timeout: int = 120) -> ToolResult:
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                output=f"Command timed out after {timeout}s",
                is_error=True,
                error_kind="timeout",
            )

        output = truncate(proc.stdout + proc.stderr)
        is_error = proc.returncode != 0

        return ToolResult(
            output=output,
            is_error=is_error,
            error_kind=classify_error(output, proc.returncode)
            if is_error
            else None,
        )
