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
    """Action the agent can take. Declare `operation` as the *kind* of
    effect the tool has — `"read"`, `"execute_low_risk"`, or
    `"execute_high_risk"` — and the agent's autonomy level decides, per
    call, whether to allow it, ask for approval, or deny it (see
    `pycodeloop.core.autonomy`). Set `concurrent_safe = True` on subclasses
    whose `run()` has no shared mutable state, so Agent may run several calls
    to the *same* tool concurrently within one batch (distinct-named tools in
    a batch already run concurrently regardless of this flag — it only
    affects repeated same-name calls). Set `wants_cancel_event = True` and
    accept a `cancel_event` keyword in `run()` for a tool that spawns its own
    long-running work (e.g. a sub-agent) and needs to notice cancellation
    itself. Set `timeout` to cap how long Agent waits for `run()` to finish
    before treating it as failed and moving on."""

    name: str
    description: str
    parameters: dict[str, Any] = {"type": "object", "properties": {}}
    operation: str = "execute_low_risk"
    concurrent_safe: bool = False
    wants_cancel_event: bool = False
    timeout: float | None = None

    @property
    def dangerous(self) -> bool:
        """Backward-compatible view: a tool is "dangerous" when its
        operation isn't a pure read. The autonomy gate is the real control
        surface now; this only exists so older callers/integrations that
        inspected `tool.dangerous` keep working."""
        return self.operation != "read"

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def preview(self, **kwargs) -> str:
        """Human-readable summary of what `run(**kwargs)` would do.

        Shown to the user in a confirmation prompt before a high-risk tool
        actually runs. Override for a diff, a shell command line, etc.
        """
        return ", ".join(f"{key}={value!r}" for key, value in kwargs.items())

    @abstractmethod
    def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError
