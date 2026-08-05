"""Provider ABC"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ProviderResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    raw: Any = None


class Provider(ABC):
    """
    Import:
        You can import the **Provider** class with:

            from aiflow.abc.provider import Provider

    Every LLM backend AIFlow can drive implements this interface. Swap
    providers by passing a different instance to `Agent(provider=...)`,
    the same way dotflow swaps `Storage`/`Notify`/`Log` implementations
    through `Config`.
    """

    name: str = "base"

    def __init__(self, model: str, api_key: str | None = None, **kwargs) -> None:
        self.model = model
        self.api_key = api_key
        self.extra = kwargs

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        messages: list,
        tools: list[dict],
    ) -> ProviderResponse:
        """Send conversation + tool schema, return the model's response."""
