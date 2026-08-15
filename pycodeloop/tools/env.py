"""Env Tool"""

from __future__ import annotations

import os
import re

from pycodeloop.abc.tool import Tool, ToolResult

_SENSITIVE_WORDS = frozenset(
    {
        "SECRET",
        "KEY",
        "TOKEN",
        "PASSWORD",
        "PASSWD",
        "PASSPHRASE",
        "PASS",
        "CREDENTIAL",
        "CREDENTIALS",
        "PRIVATE",
        "AUTH",
        "AUTHORIZATION",
        "BEARER",
        "COOKIE",
        "SESSION",
        "APIKEY",
    }
)
_CREDENTIAL_IN_URL = re.compile(r"^\w+://[^/@\s]+:[^/@\s]+@")
_SPLIT = re.compile(r"[^A-Z0-9]+")


def _mask(name: str, value: str) -> str:
    parts = [p for p in _SPLIT.split(name.upper()) if p]
    if any(part in _SENSITIVE_WORDS for part in parts):
        return "***"
    if _CREDENTIAL_IN_URL.match(value):
        return "***"
    return value


class EnvTool(Tool):
    name = "env"
    description = (
        "Read environment variables. Pass `name` for one variable, or "
        "omit it to list every variable name (values whose name looks "
        "sensitive — SECRET, KEY, TOKEN, PASS/PASSWORD, AUTH, COOKIE, "
        "SESSION, CREDENTIAL, … — or a scheme://user:pass@ credential in "
        "the value, are masked)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
    }
    dangerous = True

    def preview(self, name: str = "", **_) -> str:
        return (
            f"$ env {name}"
            if name
            else "$ env (list all variable names and masked values)"
        )

    def run(self, name: str = "") -> ToolResult:
        if name:
            value = os.environ.get(name)

            if value is None:
                return ToolResult(output=f"{name} is not set", is_error=True)

            return ToolResult(output=f"{name}={_mask(name, value)}")

        lines = [
            f"{key}={_mask(key, value)}"
            for key, value in sorted(os.environ.items())
        ]

        return ToolResult(output="\n".join(lines))
