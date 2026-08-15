"""Tests for typed failure classification (issue #39)."""

from __future__ import annotations

import unittest

from pycodeloop.abc.provider import Provider, ProviderResponse, ToolCall
from pycodeloop.abc.tool import Tool, ToolResult
from pycodeloop.core.agent import Agent
from pycodeloop.core.errors import classify_error
from pycodeloop.core.session import Session


class FakeProvider(Provider):
    name = "fake"

    def __init__(self, scripted: list[ProviderResponse]) -> None:
        super().__init__(model="fake-model")
        self._scripted = list(scripted)

    def complete(self, system_prompt, messages, tools, on_delta=None):
        return self._scripted.pop(0)


class TestClassifyError(unittest.TestCase):
    def test_syntax_error(self):
        self.assertEqual(
            classify_error(
                "Traceback...\n  File x\nSyntaxError: invalid syntax"
            ),
            "syntax_error",
        )

    def test_test_failure(self):
        self.assertEqual(
            classify_error("===== 2 failed in 0.12s =====\nFAILED x"),
            "test_failure",
        )
        self.assertEqual(
            classify_error("assert 1 == 2\nAssertionError"), "test_failure"
        )
        self.assertEqual(
            classify_error("tests failed", exit_code=1), "test_failure"
        )

    def test_permission_denied(self):
        self.assertEqual(
            classify_error("PermissionError: [Errno 13] Permission denied"),
            "permission_denied",
        )
        self.assertEqual(
            classify_error("bash: ./x: Permission denied"), "permission_denied"
        )

    def test_command_not_found(self):
        self.assertEqual(
            classify_error("bash: frobnicate: command not found"),
            "command_not_found",
        )

    def test_runtime_exception(self):
        self.assertEqual(
            classify_error(
                "Traceback (most recent call last):\n  raise ValueError('x')"
            ),
            "runtime_exception",
        )

    def test_timeout(self):
        self.assertEqual(
            classify_error("Command timed out after 120s"), "timeout"
        )

    def test_unknown_fallback(self):
        self.assertEqual(classify_error("something weird happened"), "unknown")


class BadTool(Tool):
    name = "bad"
    description = "Always fails with a test failure."

    def run(self, **kwargs) -> ToolResult:
        return ToolResult(output="FAILED tests/test_x.py", is_error=True)


class TestErrorKindInjection(unittest.TestCase):
    def test_prefix_injected_into_tool_result(self):
        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[ToolCall(id="1", name="bad", arguments={})],
                ),
                ProviderResponse(text="ok"),
            ]
        )
        agent = Agent(provider=provider, tools=[BadTool()])
        session = Session(system_prompt="sys")

        agent.run("do it", session=session)

        tool_message = next(m for m in session.messages if m.role == "tool")
        self.assertTrue(tool_message.content.startswith("[test_failure]\n"))
        self.assertIn("FAILED tests/test_x.py", tool_message.content)

    def test_error_kind_recorded_in_trace(self):
        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[ToolCall(id="1", name="bad", arguments={})],
                ),
                ProviderResponse(text="ok"),
            ]
        )
        events: list[dict] = []
        agent = Agent(
            provider=provider,
            tools=[BadTool()],
            on_trace_event=lambda e: events.append(e),
        )

        agent.run("do it")

        tool_result = next(e for e in events if e["type"] == "tool_result")
        self.assertEqual(tool_result["is_error"], True)
        self.assertEqual(tool_result["error_kind"], "test_failure")


if __name__ == "__main__":
    unittest.main()
