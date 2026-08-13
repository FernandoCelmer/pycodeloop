"""Session"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    role: str
    content: Any
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None
    images: list[str] | None = None
    """Base64-encoded PNG data, one entry per attached image."""


@dataclass
class Session:
    system_prompt: str = ""
    messages: list[Message] = field(default_factory=list)
    cwd: str = "."

    def add_user(self, text: str, images: list[str] | None = None) -> None:
        self.messages.append(Message(role="user", content=text, images=images))

    def add_assistant(self, text: str, tool_calls: list[dict] | None = None) -> None:
        self.messages.append(
            Message(role="assistant", content=text, tool_calls=tool_calls)
        )

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self.messages.append(
            Message(role="tool", content=content, tool_call_id=tool_call_id)
        )

    def history(self) -> list[Message]:
        self._repair_dangling_tool_calls()
        return self.messages

    def _repair_dangling_tool_calls(self) -> None:
        """Self-heals a session left with a trailing tool_calls message
        that has no tool_result replies — e.g. the process was killed
        (crash, force-quit) between persisting the assistant's tool_use
        message and running the tools. Every provider rejects a tool_use
        without a matching tool_result on the next call, which would
        otherwise make the session permanently unusable."""
        if not self.messages:
            return

        last = self.messages[-1]
        if last.role != "assistant" or not last.tool_calls:
            return

        for call in last.tool_calls:
            self.add_tool_result(
                call["id"], "Cancelled — connection was lost before this tool ran."
            )

    def trim(self, max_turns: int) -> None:
        """Keep only the most recent `max_turns` user-initiated turns,
        dropping older ones as a whole unit — trimming mid-turn would
        split an assistant tool_calls message from its tool_result
        replies, which every provider rejects."""
        turn_starts = [i for i, m in enumerate(self.messages) if m.role == "user"]

        if len(turn_starts) <= max_turns:
            return

        cutoff = turn_starts[-max_turns]
        self.messages = self.messages[cutoff:]
