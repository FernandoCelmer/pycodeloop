"""Session"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    role: str  # "user" | "assistant" | "tool"
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
        self.messages.append(Message(role="assistant", content=text, tool_calls=tool_calls))

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self.messages.append(Message(role="tool", content=content, tool_call_id=tool_call_id))

    def history(self) -> list[Message]:
        return self.messages
