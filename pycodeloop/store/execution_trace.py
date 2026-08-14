"""Execution trace — durable JSONL record of what a run did (provider
calls, tool calls/results, retries, compaction), for postmortem
debugging when a session misbehaves and nothing but the trace outlives
the process."""

from __future__ import annotations

import json
import time
from pathlib import Path


class JsonlTracer:
    """Callable `on_trace_event` sink: appends one JSON line per event
    to `~/.pycodeloop/logs/<session_key>.jsonl`."""

    def __init__(
        self, session_key: str, directory: Path | None = None
    ) -> None:
        base = directory or Path.home() / ".pycodeloop" / "logs"
        base.mkdir(parents=True, exist_ok=True)
        self.path = base / f"{session_key}.jsonl"

    def __call__(self, event: dict) -> None:
        line = json.dumps({"ts": time.time(), **event}, default=str)
        with self.path.open("a") as fh:
            fh.write(line + "\n")
