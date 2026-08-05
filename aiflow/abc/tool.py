"""Tool ABC"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    output: str
    is_error: bool = False


class Tool(ABC):
    """Action the agent can take. Set `dangerous = True` on subclasses that
    change state (filesystem, shell, remote calls) so Agent asks for
    confirmation before running them."""

    name: str
    description: str
    parameters: dict[str, Any] = {"type": "object", "properties": {}}
    dangerous: bool = False

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def preview(self, **kwargs) -> str:
        """Human-readable summary of what `run(**kwargs)` would do.

        Shown to the user in a confirmation prompt before a dangerous tool
        actually runs. Override for a diff, a shell command line, etc.
        """
        return ", ".join(f"{key}={value!r}" for key, value in kwargs.items())

    @abstractmethod
    def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError
