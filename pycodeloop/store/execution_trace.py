"""Execution trace — durable JSONL record of what a run did (provider
calls, tool calls/results, retries, compaction), for postmortem
debugging when a session misbehaves and nothing but the trace outlives
the process."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path


class JsonlTracer:
    """Callable `on_trace_event` sink: appends one JSON line per event
    to `~/.pycodeloop/logs/<session_key>.jsonl`. Keeps one open,
    line-buffered file handle for its lifetime, guarded by a lock, so
    concurrent `CodeLoop.run()` calls sharing a `session_key` (e.g. a
    threaded server handling overlapping requests) can't interleave
    writes mid-line."""

    def __init__(
        self, session_key: str, directory: Path | None = None
    ) -> None:
        if "/" in session_key or "\\" in session_key:
            raise ValueError(
                f"session_key {session_key!r} must not contain a path "
                "separator"
            )

        base = (directory or Path.home() / ".pycodeloop" / "logs").resolve()
        base.mkdir(parents=True, exist_ok=True)

        candidate = (base / f"{session_key}.jsonl").resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            raise ValueError(
                f"session_key {session_key!r} resolves outside the log "
                f"directory {base}"
            ) from None

        self.path = candidate
        self._lock = threading.Lock()
        self._fh = self.path.open("a", buffering=1)

    def __call__(self, event: dict) -> None:
        line = json.dumps({"ts": time.time(), **event}, default=str)
        with self._lock:
            self._fh.write(line + "\n")

    def close(self) -> None:
        with self._lock:
            self._fh.close()

    def __del__(self) -> None:
        fh = getattr(self, "_fh", None)
        if fh is not None and not fh.closed:
            fh.close()
