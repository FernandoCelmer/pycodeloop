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
    confirmation before running them. Set `concurrent_safe = True` on
    subclasses whose `run()` has no shared mutable state, so Agent may
    run several calls to the *same* tool concurrently within one batch
    (distinct-named tools in a batch already run concurrently regardless
    of this flag — it only affects repeated same-name calls)."""

    name: str
    description: str
    parameters: dict[str, Any] = {"type": "object", "properties": {}}
    dangerous: bool = False
    concurrent_safe: bool = False

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
