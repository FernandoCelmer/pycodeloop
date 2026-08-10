"""Shared output-size cap for tools whose output size isn't bounded by
the caller (command output, file contents, search results) — without
one, a single verbose command or large file blows out the LLM's
context on every turn it stays in history."""

from __future__ import annotations

MAX_OUTPUT_CHARS = 20000


def truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text

    return text[:MAX_OUTPUT_CHARS] + "\n… (truncated)"
