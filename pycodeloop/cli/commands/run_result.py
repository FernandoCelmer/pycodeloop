"""Outcome of a `pycodeloop run` invocation, serialized for --ci/--output json."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

EXIT_CODE_SUCCESS = 0
EXIT_CODE_ERROR = 1
EXIT_CODE_REGRESSION = 2
EXIT_CODE_BUDGET = 3

_MODIFYING_ACTIONS = {"write", "edit", "delete"}


@dataclass
class RunResult:
    status: str
    turns: int = 0
    tokens: dict[str, int] = field(
        default_factory=lambda: {"input": 0, "output": 0}
    )
    cost_usd: float | None = None
    regression: bool = False
    files_modified: list[str] = field(default_factory=list)
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def exit_code_for(result: RunResult) -> int:
    """Map a run outcome to a shell exit code.

    0 success · 1 agent error/max-turns/cancelled · 2 regression · 3 budget.
    """
    if result.status == "budget":
        return EXIT_CODE_BUDGET
    if result.regression:
        return EXIT_CODE_REGRESSION
    if result.status in {"error", "max_turns", "cancelled"}:
        return EXIT_CODE_ERROR
    return EXIT_CODE_SUCCESS


def files_modified_from(history: list) -> list[str]:
    """Unique paths touched by a write/edit/delete in `FileAccessRecord` rows."""
    modified: list[str] = []
    for record in history:
        if record.action in _MODIFYING_ACTIONS and record.path not in modified:
            modified.append(record.path)
    return modified
