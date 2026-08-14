from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    role: str
    content: Any
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None
    images: list[str] | None = None
    """Base64-encoded PNG data, one entry per attached image."""
