"""Bash Tool"""

from __future__ import annotations

import subprocess

from aiflow.abc.tool import Tool, ToolResult


class BashTool(Tool):
    name = "bash"
    description = "Run a shell command and return its stdout/stderr."
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
                output=f"Command timed out after {timeout}s", is_error=True
            )

        output = proc.stdout + proc.stderr
        return ToolResult(output=output, is_error=proc.returncode != 0)
