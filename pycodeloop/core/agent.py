"""Agent module"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from pycodeloop.abc.confirm import Confirm
from pycodeloop.abc.provider import Provider, Usage
from pycodeloop.abc.tool import Tool
from pycodeloop.core.context_window import context_window_for
from pycodeloop.core.session import Message, Session
from pycodeloop.core.tools import DEFAULT_TOOLS

_COMPACT_KEEP_RECENT_TURNS = 2
_COMPACT_SUMMARY_PROMPT = (
    "Summarize the conversation so far in a concise paragraph, preserving "
    "concrete facts, decisions, file paths, and any unfinished work — this "
    "summary replaces the full history, so don't drop anything needed to "
    "continue the task."
)

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
        max_history_turns: int | None = None,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, str, bool], None] | None = None,
        on_text_delta: Callable[[str], None] | None = None,
        confirm: Callable[[str, str], bool | str] | Confirm | None = None,
        on_usage: Callable[[Usage, Usage, float], None] | None = None,
        on_request: Callable[[int, int], None] | None = None,
        auto_compact: bool = True,
        compact_threshold: float = 0.8,
        on_context: Callable[[int, int], None] | None = None,
        on_compact_start: Callable[[], None] | None = None,
        on_compact_end: Callable[[int, int], None] | None = None,
        on_message: Callable[[], None] | None = None,
    ) -> None:
        self.provider = provider
        self.tools = {tool.name: tool for tool in (tools or DEFAULT_TOOLS)}
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.max_history_turns = max_history_turns
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self.on_text_delta = on_text_delta
        self.confirm = confirm
        self.on_usage = on_usage
        self.on_request = on_request
        self.auto_compact = auto_compact
        self.compact_threshold = compact_threshold
        self.on_context = on_context
        self.on_compact_start = on_compact_start
        self.on_compact_end = on_compact_end
        self.on_message = on_message
        self.usage = Usage()
        self._last_context_tokens = 0

    def _notify_message(self) -> None:
        """Fired after every message is appended to the session — lets a
        caller persist incrementally instead of only after the whole
        (possibly long, multi-tool-call) turn finishes, so a crash
        mid-turn doesn't lose everything already done in it."""
        if self.on_message:
            self.on_message()

    def _tool_schemas(self) -> list[dict]:
        return [tool.schema() for tool in self.tools.values()]

    def _execute(self, name: str, arguments: dict) -> tuple[str, bool]:
        tool = self.tools.get(name)

        if tool is None:
            return f"Unknown tool: {name}", True

        if tool.dangerous and self.confirm is not None:
            preview = tool.preview(**arguments)
            ask = (
                self.confirm.ask if isinstance(self.confirm, Confirm) else self.confirm
            )
            answer = ask(name, preview)
            if answer is not True:
                if isinstance(answer, str) and answer:
                    return f"User declined and said: {answer}", True
                return "User declined to run this tool.", True

        try:
            result = tool.run(**arguments)
        except Exception as exc:
            # A tool_calls message was already added to the session before
            # `_execute` runs — an unhandled exception here would leave it
            # without its matching tool_result, which every provider
            # rejects on the next call (and `Session.trim()` can't safely
            # split them either). Report the failure as this tool's
            # result instead of crashing the whole conversation.
            return f"Tool '{name}' raised {exc.__class__.__name__}: {exc}", True

        return result.output, result.is_error

    def _compact(self, session: Session) -> None:
        """Summarize everything but the most recent turns via the
        provider itself, replacing the older history with one condensed
        message — keeps the conversation going instead of hitting the
        model's context limit."""
        turn_starts = [i for i, m in enumerate(session.messages) if m.role == "user"]

        if len(turn_starts) <= _COMPACT_KEEP_RECENT_TURNS:
            return

        if self.on_compact_start:
            self.on_compact_start()

        before_count = len(session.messages)
        cutoff = turn_starts[-_COMPACT_KEEP_RECENT_TURNS]
        older, recent = session.messages[:cutoff], session.messages[cutoff:]

        summary = self.provider.complete(
            system_prompt="Summarize conversations concisely for context compaction.",
            messages=[*older, Message(role="user", content=_COMPACT_SUMMARY_PROMPT)],
            tools=[],
        )
        self.usage = self.usage + summary.usage

        session.messages = [
            Message(
                role="assistant",
                content=f"[Earlier conversation summary]\n{summary.text}",
            ),
            *recent,
        ]
        self._notify_message()

        if self.on_compact_end:
            self.on_compact_end(before_count, len(session.messages))

    def run(
        self,
        prompt: str,
        session: Session | None = None,
        images: list[str] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> str:
        """Runs until the model stops calling tools, `max_turns` is hit,
        or `cancel_event` is set — checked at each turn boundary and
        before every tool call, never mid-request, so an in-flight
        provider call always finishes first."""
        session = session or Session(system_prompt=self.system_prompt)
        session.add_user(prompt, images=images)
        self._notify_message()

        if self.max_history_turns is not None:
            session.trim(self.max_history_turns)

        context_window = context_window_for(self.provider.model)

        for _ in range(self.max_turns):
            if cancel_event and cancel_event.is_set():
                return "Cancelled by user."

            if self.auto_compact and self._last_context_tokens >= (
                context_window * self.compact_threshold
            ):
                self._compact(session)

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

            self._last_context_tokens = response.usage.input_tokens
            if self.on_context:
                self.on_context(self._last_context_tokens, context_window)

            tool_calls = [
                {"id": call.id, "name": call.name, "arguments": call.arguments}
                for call in response.tool_calls
            ]
            session.add_assistant(response.text, tool_calls=tool_calls or None)
            self._notify_message()

            if not response.tool_calls:
                return response.text

            for call in response.tool_calls:
                if self.on_tool_call:
                    self.on_tool_call(call.name, call.arguments)

                if cancel_event and cancel_event.is_set():
                    result_text, is_error = "Cancelled by user.", True
                else:
                    result_text, is_error = self._execute(call.name, call.arguments)

                if self.on_tool_result:
                    self.on_tool_result(call.name, result_text, is_error)

                session.add_tool_result(call.id, result_text)
                self._notify_message()

            if cancel_event and cancel_event.is_set():
                return "Cancelled by user."

        return "Reached max_turns without finishing."
