"""Web Tool"""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from codeloop.abc.tool import Tool, ToolResult
from codeloop.core.tools._net import is_blocked_host

_MAX_CHARS = 20000
_SKIP_TAGS = {"script", "style", "noscript"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self.chunks.append(data.strip())


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return "\n".join(parser.chunks)


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetch a URL and return its content as plain text."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "timeout": {"type": "number", "default": 30},
        },
        "required": ["url"],
    }

    def run(self, url: str, timeout: float = 30) -> ToolResult:
        hostname = urlparse(url).hostname
        if not hostname or is_blocked_host(hostname):
            return ToolResult(
                output=f"Refused to fetch {url}: host is not a public address",
                is_error=True,
            )

        try:
            response = httpx.get(url, timeout=timeout, follow_redirects=False)
        except httpx.HTTPError as exc:
            return ToolResult(output=f"Error fetching {url}: {exc}", is_error=True)

        if response.is_redirect:
            return ToolResult(
                output=f"{url} redirects to "
                f"{response.headers.get('location')} — fetch that URL "
                "directly if it's safe to follow",
                is_error=True,
            )
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return ToolResult(output=f"Error fetching {url}: {exc}", is_error=True)

        content_type = response.headers.get("content-type", "")
        text = _html_to_text(response.text) if "html" in content_type else response.text

        if len(text) > _MAX_CHARS:
            text = text[:_MAX_CHARS] + "\n… (truncated)"
        return ToolResult(output=text)
