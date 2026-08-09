"""HTTP Request Tool"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from codeloop.abc.tool import Tool, ToolResult
from codeloop.core.tools._net import is_blocked_host

_MAX_CHARS = 20000
_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


class HttpRequestTool(Tool):
    name = "http_request"
    description = (
        "Call a JSON HTTP API — any method, headers, and body. Use "
        "web_fetch instead for reading a webpage's text."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "method": {"type": "string", "default": "GET"},
            "headers": {"type": "object"},
            "json_body": {
                "type": "object",
                "description": "Sent as the JSON request body.",
            },
            "timeout": {"type": "number", "default": 30},
        },
        "required": ["url"],
    }
    dangerous = True

    def preview(
        self,
        url: str,
        method: str = "GET",
        headers: dict | None = None,
        json_body: dict | None = None,
        **_,
    ) -> str:
        lines = [f"$ {method.upper()} {url}"]
        if headers:
            lines.append(f"headers: {headers}")
        if json_body is not None:
            lines.append(f"body: {json_body}")
        return "\n".join(lines)

    def run(
        self,
        url: str,
        method: str = "GET",
        headers: dict | None = None,
        json_body: dict | None = None,
        timeout: float = 30,
    ) -> ToolResult:
        method = method.upper()
        if method not in _METHODS:
            return ToolResult(output=f"Unsupported method: {method}", is_error=True)

        hostname = urlparse(url).hostname
        if not hostname or is_blocked_host(hostname):
            return ToolResult(
                output=f"Refused to call {url}: host is not a public address",
                is_error=True,
            )

        try:
            response = httpx.request(
                method,
                url,
                headers=headers,
                json=json_body,
                timeout=timeout,
                follow_redirects=False,
            )
        except httpx.HTTPError as exc:
            return ToolResult(output=f"Error calling {url}: {exc}", is_error=True)

        if response.is_redirect:
            return ToolResult(
                output=f"{url} redirects to "
                f"{response.headers.get('location')} — call that URL "
                "directly if it's safe to follow",
                is_error=True,
            )

        text = response.text
        if len(text) > _MAX_CHARS:
            text = text[:_MAX_CHARS] + "\n… (truncated)"

        summary = f"{response.status_code} {response.reason_phrase}\n{text}"
        return ToolResult(output=summary, is_error=response.is_error)
