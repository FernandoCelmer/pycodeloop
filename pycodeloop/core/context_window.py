"""Known context-window sizes (in tokens), used to decide when a
session is close enough to a model's limit to compact it."""

from __future__ import annotations

DEFAULT_CONTEXT_WINDOW = 128_000

_CONTEXT_WINDOWS = {
    "claude-opus-5": 200_000,
    "claude-sonnet-5": 200_000,
    "claude-haiku-4-5": 200_000,
    "claude-3": 200_000,
    "gpt-5": 400_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "o1": 200_000,
    "llama3.1": 128_000,
    "llama3": 8_000,
}


def context_window_for(model: str) -> int:
    """Substring match against known model families (version/date
    suffixes like `-20260101` are common), falling back to a
    conservative default for anything unrecognized."""

    for key, size in _CONTEXT_WINDOWS.items():
        if key in model:
            return size

    return DEFAULT_CONTEXT_WINDOW
