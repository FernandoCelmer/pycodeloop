"""Usage Tracking"""

from __future__ import annotations

from pycodeloop.abc.settings import Settings
from pycodeloop.core.store.json_store import default_store

_SECTION = "usage"
_EMPTY_ENTRY = {"input_tokens": 0, "output_tokens": 0, "runs": 0}


class UsageTracker:
    """Cumulative token counts per `session_key` (or "global" for runs
    with none) in `~/.pycodeloop/config.json` under "usage"."""

    def __init__(self, store: Settings | None = None) -> None:
        self.store = store or default_store

    def record_usage(self, key: str, input_tokens: int, output_tokens: int) -> None:
        usage = self.store.get_section(_SECTION)
        entry = usage.get(key, dict(_EMPTY_ENTRY))
        entry["input_tokens"] += input_tokens
        entry["output_tokens"] += output_tokens
        entry["runs"] += 1
        usage[key] = entry

        self.store.set_section(_SECTION, usage)

    def get_usage(self, key: str = "global") -> dict:
        return self.store.get_section(_SECTION).get(key, dict(_EMPTY_ENTRY))
