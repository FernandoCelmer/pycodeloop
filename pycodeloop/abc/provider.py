"""Provider ABC"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    extra: dict[str, Any] | None = None


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


@dataclass
class ProviderResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    usage: Usage = field(default_factory=Usage)
    raw: Any = None


class Provider(ABC):
    """
    Import:
        You can import the **Provider** class with:

            from pycodeloop.abc.provider import Provider

    Every LLM backend CodeLoop can drive implements this interface. Swap
    providers by passing a different instance to `Agent(provider=...)`
    or `Config(provider=...)`.
    """

    name: str = "base"

    def __init__(
        self, model: str, api_key: str | None = None, **kwargs
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.extra = kwargs

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        messages: list,
        tools: list[dict],
        on_delta: Callable[[str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> ProviderResponse:
        """Send conversation + tool schema, return the model's response.

        When `on_delta` is given, call it with each text chunk as it
        arrives instead of only returning the assembled text at the end.

        When `cancel_event` is given and set while streaming, the
        implementation should stop reading as soon as practical and
        return with `stop_reason="cancelled"` instead of waiting for the
        provider to finish on its own.
        """
