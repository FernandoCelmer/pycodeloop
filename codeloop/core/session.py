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


@dataclass
class Session:
    system_prompt: str = ""
    messages: list[Message] = field(default_factory=list)
    cwd: str = "."

    def add_user(self, text: str) -> None:
        self.messages.append(Message(role="user", content=text))

    def add_assistant(self, text: str, tool_calls: list[dict] | None = None) -> None:
        self.messages.append(
            Message(role="assistant", content=text, tool_calls=tool_calls)
        )

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self.messages.append(
            Message(role="tool", content=content, tool_call_id=tool_call_id)
        )

    def history(self) -> list[Message]:
        return self.messages

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
