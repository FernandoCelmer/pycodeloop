"""Usage tracking — cumulative token counts in ~/.codeloop/config.json"""

from __future__ import annotations

from codeloop.core.local_config import get_section, set_section

_SECTION = "usage"
_EMPTY_ENTRY = {"input_tokens": 0, "output_tokens": 0, "runs": 0}


def record_usage(key: str, input_tokens: int, output_tokens: int) -> None:
    """Add `input_tokens`/`output_tokens` to the running total for `key`
    (a `session_key`, or "global" for runs with none) and bump its run
    count by one."""
    usage = get_section(_SECTION)
    entry = usage.get(key, dict(_EMPTY_ENTRY))
    entry["input_tokens"] += input_tokens
    entry["output_tokens"] += output_tokens
    entry["runs"] += 1
    usage[key] = entry

    set_section(_SECTION, usage)


def get_usage(key: str = "global") -> dict:
    """Return the cumulative {input_tokens, output_tokens, runs} for
    `key` — all zero if it was never recorded."""
    return get_section(_SECTION).get(key, dict(_EMPTY_ENTRY))
