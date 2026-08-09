"""Agent module"""

from __future__ import annotations

import time
from collections.abc import Callable

from codeloop.abc.provider import Provider, Usage
from codeloop.abc.tool import Tool
from codeloop.core.session import Session
from codeloop.core.tools import DEFAULT_TOOLS

DEFAULT_SYSTEM_PROMPT = (
    "You are CodeLoop, an autonomous coding agent. You have tools to read, "
    "write, edit, and delete files, list directories, search the codebase "
    "(grep/glob), fetch web pages, and run shell commands. Use them to "
    "accomplish the user's request directly instead of only describing "
    "what to do. Investigate before acting: read relevant files and search "
    "for existing patterns rather than guessing. Prefer the smallest change "
    "that solves the request. Be concise — state what you did, not what "
    "you're about to do."
)


class Agent:
    """Drives a provider through a tool-use loop until it stops."""

    def __init__(
        self,
        provider: Provider,
        tools: list[Tool] | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_turns: int = 25,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, str, bool], None] | None = None,
        on_text_delta: Callable[[str], None] | None = None,
        confirm: Callable[[str, str], bool | str] | None = None,
        on_usage: Callable[[Usage, Usage, float], None] | None = None,
        on_request: Callable[[int, int], None] | None = None,
    ) -> None:
        self.provider = provider
        self.tools = {tool.name: tool for tool in (tools or DEFAULT_TOOLS)}
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self.on_text_delta = on_text_delta
        self.confirm = confirm
        self.on_usage = on_usage
        self.on_request = on_request
        self.usage = Usage()

    def _tool_schemas(self) -> list[dict]:
        return [tool.schema() for tool in self.tools.values()]

    def _execute(self, name: str, arguments: dict) -> tuple[str, bool]:
        tool = self.tools.get(name)
        if tool is None:
            return f"Unknown tool: {name}", True

        if tool.dangerous and self.confirm is not None:
            preview = tool.preview(**arguments)
            answer = self.confirm(name, preview)
            if answer is not True:
                if isinstance(answer, str) and answer:
                    return f"User declined and said: {answer}", True
                return "User declined to run this tool.", True

        result = tool.run(**arguments)
        return result.output, result.is_error

    def run(self, prompt: str, session: Session | None = None) -> str:
        session = session or Session(system_prompt=self.system_prompt)
        session.add_user(prompt)

        for _ in range(self.max_turns):
            tools = self._tool_schemas()
            if self.on_request:
                self.on_request(len(session.history()), len(tools))

            started_at = time.perf_counter()
            response = self.provider.complete(
                system_prompt=self.system_prompt,
                messages=session.history(),
                tools=tools,
                on_delta=self.on_text_delta,
            )
            elapsed = time.perf_counter() - started_at

            self.usage = self.usage + response.usage
            if self.on_usage:
                self.on_usage(response.usage, self.usage, elapsed)

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

                result_text, is_error = self._execute(call.name, call.arguments)

                if self.on_tool_result:
                    self.on_tool_result(call.name, result_text, is_error)

                session.add_tool_result(call.id, result_text)

        return "Reached max_turns without finishing."
