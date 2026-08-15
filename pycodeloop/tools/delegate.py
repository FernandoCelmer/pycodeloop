"""Delegate Tool — spawn a read-only sub-agent for an independent subtask."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from pycodeloop.abc.tool import Tool, ToolResult

if TYPE_CHECKING:
    from pycodeloop.abc.provider import Provider

_DEFAULT_MAX_TURNS = 15


class DelegateTool(Tool):
    name = "delegate"
    description = (
        "Delegate an independent, self-contained subtask to a fresh "
        "sub-agent with its own context window. The sub-agent only has "
        "read-only tools (read_file, list_dir, glob, grep, git status/"
        "diff/log, web_fetch) — it cannot write, edit, delete, or run "
        "shell commands. Use it for research, wide multi-file "
        "investigation, or summarizing a large area of the codebase — "
        "not for tasks that need to change anything. Call it multiple "
        "times in the same turn to run several sub-agents in parallel. "
        "Each call starts with no conversation history, so give it every "
        "path, constraint, and question it needs in `task`; only its "
        "final answer comes back, not its intermediate steps."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": (
                    "The complete, self-contained task for the sub-agent."
                ),
            },
        },
        "required": ["task"],
    }
    concurrent_safe = True
    wants_cancel_event = True

    def __init__(
        self,
        provider: Provider,
        tools: list[Tool],
        max_turns: int = _DEFAULT_MAX_TURNS,
    ) -> None:
        self.provider = provider
        self.tools = tools
        self.max_turns = max_turns
        self.timeout = max_turns * getattr(provider, "timeout", 60.0)

    def preview(self, task: str, **_) -> str:
        return task

    def run(
        self, task: str, cancel_event: threading.Event | None = None
    ) -> ToolResult:
        from pycodeloop.core.agent import Agent

        sub_agent = Agent(
            provider=self.provider,
            tools=self.tools,
            max_turns=self.max_turns,
        )
        text = sub_agent.run(task, cancel_event=cancel_event)
        return ToolResult(output=text)
