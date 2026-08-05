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
    name: str
    description: str
    parameters: dict[str, Any] = {"type": "object", "properties": {}}

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    @abstractmethod
    def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError
