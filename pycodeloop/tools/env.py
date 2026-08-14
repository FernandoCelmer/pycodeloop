"""Env Tool"""

from __future__ import annotations

import os

from pycodeloop.abc.tool import Tool, ToolResult

_SENSITIVE_MARKERS = ("SECRET", "KEY", "TOKEN", "PASSWORD", "CREDENTIAL")


def _mask(name: str, value: str) -> str:
    upper = name.upper()
    if any(marker in upper for marker in _SENSITIVE_MARKERS):
        return "***"
    return value


class EnvTool(Tool):
    name = "env"
    description = (
        "Read environment variables. Pass `name` for one variable, or "
        "omit it to list every variable name (values containing SECRET, "
        "KEY, TOKEN, PASSWORD, or CREDENTIAL are masked)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
    }

    def run(self, name: str = "") -> ToolResult:
        if name:
            value = os.environ.get(name)

            if value is None:
                return ToolResult(output=f"{name} is not set", is_error=True)

            return ToolResult(output=f"{name}={_mask(name, value)}")

        lines = [
            f"{key}={_mask(key, value)}" for key, value in sorted(os.environ.items())
        ]

        return ToolResult(output="\n".join(lines))
