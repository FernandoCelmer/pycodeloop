"""Session"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from pycodeloop.protocol.messages import Message

__all__ = ["Message", "Session"]


@dataclass
class Session:
    system_prompt: str = ""
    messages: list[Message] = field(default_factory=list)
    cwd: str = "."
    dirty: bool = field(default=False, repr=False, compare=False)
    last_context_tokens: int = field(default=0, repr=False, compare=False)
    _lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False
    )

    def add_user(self, text: str, images: list[str] | None = None) -> None:
        with self._lock:
            self.messages.append(
                Message(role="user", content=text, images=images)
            )

    def add_assistant(
        self, text: str, tool_calls: list[dict] | None = None
    ) -> None:
        with self._lock:
            self.messages.append(
                Message(role="assistant", content=text, tool_calls=tool_calls)
            )

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        with self._lock:
            self.messages.append(
                Message(
                    role="tool", content=content, tool_call_id=tool_call_id
                )
            )

    def history(self) -> list[Message]:
        with self._lock:
            self._repair_dangling_tool_calls()
            return list(self.messages)

    def _repair_dangling_tool_calls(self) -> None:
        """Self-heals any assistant tool_calls message left without a
        matching tool_result immediately after it, anywhere in history.
        Caller must hold `self._lock`."""
        i = 0
        while i < len(self.messages):
            msg = self.messages[i]
            if msg.role != "assistant" or not msg.tool_calls:
                i += 1
                continue

            j = i + 1
            satisfied_ids = set()
            while j < len(self.messages) and self.messages[j].role == "tool":
                satisfied_ids.add(self.messages[j].tool_call_id)
                j += 1

            missing = [
                call
                for call in msg.tool_calls
                if call["id"] not in satisfied_ids
            ]
            for offset, call in enumerate(missing):
                self.messages.insert(
                    j + offset,
                    Message(
                        role="tool",
                        content="Cancelled — connection was lost before this tool ran.",
                        tool_call_id=call["id"],
                    ),
                )
            if missing:
                self.dirty = True
            i = j + len(missing)

    def replace_messages(self, messages: list[Message]) -> None:
        """Swap in a whole new message list — e.g. compaction replacing
        older history with a condensed summary. Holding the same lock
        `add_*` uses closes the race where a tool-result thread appends
        to the list being discarded right as it's replaced. Marks the
        session `dirty` so storage backends that append incrementally
        (tracking a message-count watermark) know to do a full rewrite
        on the next save instead of trusting the watermark."""
        with self._lock:
            self.messages = messages
            self.dirty = True

    def trim(self, max_turns: int) -> None:
        """Keep only the most recent `max_turns` user-initiated turns,
        dropping older ones as a whole unit — trimming mid-turn would
        split an assistant tool_calls message from its tool_result
        replies, which every provider rejects."""
        with self._lock:
            turn_starts = [
                i for i, m in enumerate(self.messages) if m.role == "user"
            ]

            if len(turn_starts) <= max_turns:
                return

            cutoff = turn_starts[-max_turns]
            self.messages = self.messages[cutoff:]
            self.dirty = True
