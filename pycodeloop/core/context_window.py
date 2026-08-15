"""Known context-window sizes (in tokens), used to decide when a
session is close enough to a model's limit to compact it."""

from __future__ import annotations

DEFAULT_CONTEXT_WINDOW = 128_000

_CONTEXT_WINDOWS = {
    "claude-opus-5": 200_000,
    "claude-sonnet-5": 200_000,
    "claude-haiku-4-5": 200_000,
    "claude-fable-5": 200_000,
    "claude-opus-4": 200_000,
    "claude-sonnet-4": 200_000,
    "claude-haiku-3-5": 200_000,
    "claude-3": 200_000,
    "gpt-5": 400_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "o1": 200_000,
    "o3": 200_000,
    "o4": 200_000,
    "gpt-oss": 128_000,
    "gemini-3": 1_000_000,
    "gemini-2.5": 1_000_000,
    "grok-4": 256_000,
    "grok-3": 131_072,
    "grok-build": 128_000,
    "llama-3.3-70b-versatile": 128_000,
    "kimi-k3": 256_000,
    "kimi-k2": 128_000,
    "moonshot": 128_000,
    "deepseek-v4-pro": 128_000,
    "deepseek-v4-flash": 64_000,
    "deepseek-chat": 64_000,
    "deepseek-reasoner": 128_000,
    "llama-3.3-70b": 128_000,
    "llama3.1": 128_000,
    "llama3": 8_000,
    "qwen3": 128_000,
    "qwen2.5": 128_000,
    "qwen-max": 128_000,
    "qwen-plus": 128_000,
    "qwen-turbo": 128_000,
}


def context_window_for(model: str) -> int:
    """Case-insensitive substring match against known model families
    (version/date suffixes like `-20260101` are common, and vendors are
    inconsistent about casing — e.g. Together AI's `Llama-3.3-70B`),
    falling back to a conservative default for anything unrecognized —
    low enough that compaction fires early rather than letting an
    oversized context hit the provider's real limit and get rejected."""
    lowered = model.lower()

    for key, size in _CONTEXT_WINDOWS.items():
        if key in lowered:
            return size

    return DEFAULT_CONTEXT_WINDOW
