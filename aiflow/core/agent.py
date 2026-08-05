"""Agent module"""

from __future__ import annotations

from collections.abc import Callable

from aiflow.abc.provider import Provider
from aiflow.abc.tool import Tool
from aiflow.core.session import Session
from aiflow.core.tools import DEFAULT_TOOLS

DEFAULT_SYSTEM_PROMPT = (
    "You are AIFlow, an autonomous coding agent. You have tools to read, "
    "write, and edit files, search the codebase, and run shell commands. "
    "Use them to accomplish the user's request. Be direct and make changes "
    "instead of only describing them."
)


class Agent:
    """Drives a provider through a tool-use loop until it stops calling tools."""

    def __init__(
        self,
        provider: Provider,
        tools: list[Tool] | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_turns: int = 25,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, str], None] | None = None,
    ) -> None:
        self.provider = provider
        self.tools = {tool.name: tool for tool in (tools or DEFAULT_TOOLS)}
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result

    def _tool_schemas(self) -> list[dict]:
        return [tool.schema() for tool in self.tools.values()]

    def run(self, prompt: str, session: Session | None = None) -> str:
        session = session or Session(system_prompt=self.system_prompt)
        session.add_user(prompt)

        for _ in range(self.max_turns):
            response = self.provider.complete(
                system_prompt=self.system_prompt,
                messages=session.history(),
                tools=self._tool_schemas(),
            )

            tool_calls = [
                {"id": call.id, "name": call.name, "arguments": call.arguments}
                for call in response.tool_calls
            ]
            session.add_assistant(response.text, tool_calls=tool_calls or None)

            if not response.tool_calls:
                return response.text

            for call in response.tool_calls:
                if self.on_tool_call:
                    self.on_tool_call(call.name, call.arguments)

                tool = self.tools.get(call.name)
                if tool is None:
                    result_text = f"Unknown tool: {call.name}"
                else:
                    result = tool.run(**call.arguments)
                    result_text = result.output

                if self.on_tool_result:
                    self.on_tool_result(call.name, result_text)

                session.add_tool_result(call.id, result_text)

        return "Reached max_turns without finishing."
