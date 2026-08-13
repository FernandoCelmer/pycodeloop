"""Test Agent class"""

import threading
import unittest
from unittest import mock

from pycodeloop.abc.confirm import Confirm
from pycodeloop.abc.provider import Provider, ProviderResponse, ToolCall, Usage
from pycodeloop.abc.tool import Tool, ToolResult
from pycodeloop.core.agent import Agent
from pycodeloop.core.session import Session


class FakeProvider(Provider):
    name = "fake"

    def __init__(self, scripted: list[ProviderResponse]) -> None:
        super().__init__(model="fake-model")
        self._scripted = list(scripted)

    def complete(
        self, system_prompt, messages, tools, on_delta=None
    ) -> ProviderResponse:
        return self._scripted.pop(0)


class EchoTool(Tool):
    name = "echo"
    description = "Echo the given text."
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def run(self, text: str) -> ToolResult:
        return ToolResult(output=f"echo: {text}")


class FailTool(Tool):
    name = "fail"
    description = "Always fails."

    def run(self, **kwargs) -> ToolResult:
        return ToolResult(output="boom", is_error=True)


class DeleteTool(Tool):
    name = "delete_everything"
    description = "Deletes everything."
    dangerous = True

    def run(self, **kwargs) -> ToolResult:
        return ToolResult(output="deleted")


class TestAgent(unittest.TestCase):
    def test_returns_text_when_no_tool_calls(self):
        provider = FakeProvider([ProviderResponse(text="hello")])
        agent = Agent(provider=provider, tools=[EchoTool()])

        result = agent.run("hi")

        self.assertEqual(result, "hello")

    def test_executes_tool_call_then_returns_final_text(self):
        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[
                        ToolCall(id="1", name="echo", arguments={"text": "hey"})
                    ],
                ),
                ProviderResponse(text="done"),
            ]
        )
        calls = []
        agent = Agent(
            provider=provider,
            tools=[EchoTool()],
            on_tool_result=lambda name, result, is_error: calls.append(
                (name, result, is_error)
            ),
        )

        result = agent.run("do it")

        self.assertEqual(result, "done")
        self.assertEqual(calls, [("echo", "echo: hey", False)])

    def test_reports_unknown_tool(self):
        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[ToolCall(id="1", name="missing", arguments={})],
                ),
                ProviderResponse(text="ok"),
            ]
        )
        results = []
        agent = Agent(
            provider=provider,
            tools=[EchoTool()],
            on_tool_result=lambda _name, result, _is_error: results.append(result),
        )

        agent.run("do it")

        self.assertEqual(results, ["Unknown tool: missing"])

    def test_reports_tool_is_error_flag(self):
        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[ToolCall(id="1", name="fail", arguments={})],
                ),
                ProviderResponse(text="ok"),
            ]
        )
        calls = []
        agent = Agent(
            provider=provider,
            tools=[FailTool()],
            on_tool_result=lambda name, result, is_error: calls.append(
                (name, result, is_error)
            ),
        )

        agent.run("do it")

        self.assertEqual(calls, [("fail", "boom", True)])

    def test_skips_dangerous_tool_when_confirm_declines(self):
        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[
                        ToolCall(id="1", name="delete_everything", arguments={})
                    ],
                ),
                ProviderResponse(text="ok"),
            ]
        )
        results = []
        agent = Agent(
            provider=provider,
            tools=[DeleteTool()],
            confirm=lambda _name, _preview: False,
            on_tool_result=lambda _name, result, _is_error: results.append(result),
        )

        agent.run("do it")

        self.assertEqual(results, ["User declined to run this tool."])

    def test_runs_dangerous_tool_when_confirm_accepts(self):
        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[
                        ToolCall(id="1", name="delete_everything", arguments={})
                    ],
                ),
                ProviderResponse(text="ok"),
            ]
        )
        results = []
        agent = Agent(
            provider=provider,
            tools=[DeleteTool()],
            confirm=lambda _name, _preview: True,
            on_tool_result=lambda _name, result, _is_error: results.append(result),
        )

        agent.run("do it")

        self.assertEqual(results, ["deleted"])

    def test_accepts_confirm_abc_instance_instead_of_callable(self):
        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[
                        ToolCall(id="1", name="delete_everything", arguments={})
                    ],
                ),
                ProviderResponse(text="ok"),
            ]
        )

        class AlwaysConfirm(Confirm):
            def ask(self, name: str, preview: str) -> bool | str:
                return True

        results = []
        agent = Agent(
            provider=provider,
            tools=[DeleteTool()],
            confirm=AlwaysConfirm(),
            on_tool_result=lambda _name, result, _is_error: results.append(result),
        )

        agent.run("do it")

        self.assertEqual(results, ["deleted"])

    def test_on_request_fires_before_each_provider_call(self):
        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[ToolCall(id="1", name="echo", arguments={"text": "x"})],
                ),
                ProviderResponse(text="done"),
            ]
        )
        calls = []
        agent = Agent(
            provider=provider,
            tools=[EchoTool()],
            on_request=lambda messages, tools: calls.append((messages, tools)),
        )

        agent.run("do it")

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], (1, 1))

    def test_max_history_turns_trims_session_before_each_run(self):
        session = Session(system_prompt="sys")
        session.add_user("old-1")
        session.add_assistant("old-1-reply")
        session.add_user("old-2")
        session.add_assistant("old-2-reply")

        provider = FakeProvider([ProviderResponse(text="new-reply")])
        agent = Agent(provider=provider, max_history_turns=1)

        agent.run("new", session=session)

        contents = [m.content for m in session.messages]
        self.assertEqual(contents, ["new", "new-reply"])

    def test_no_max_history_turns_leaves_session_unbounded(self):
        session = Session(system_prompt="sys")
        session.add_user("old-1")
        session.add_assistant("old-1-reply")

        provider = FakeProvider([ProviderResponse(text="new-reply")])
        agent = Agent(provider=provider)

        agent.run("new", session=session)

        self.assertEqual(len(session.messages), 4)

    def test_on_usage_reports_elapsed_time(self):
        provider = FakeProvider([ProviderResponse(text="hello")])
        seen = []
        agent = Agent(
            provider=provider,
            on_usage=lambda _turn, _total, elapsed: seen.append(elapsed),
        )

        agent.run("hi")

        self.assertEqual(len(seen), 1)
        self.assertGreaterEqual(seen[0], 0)

    def test_on_context_reports_tokens_against_known_window(self):
        provider = FakeProvider(
            [ProviderResponse(text="hi", usage=Usage(input_tokens=42))]
        )
        provider.model = "claude-sonnet-5"
        seen = []
        agent = Agent(provider=provider, on_context=lambda *args: seen.append(args))

        agent.run("hi")

        self.assertEqual(seen, [(42, 200_000)])

    def test_compacts_when_context_usage_crosses_threshold(self):
        provider = FakeProvider(
            [
                ProviderResponse(text="reply-1", usage=Usage(input_tokens=190_000)),
                ProviderResponse(text="reply-2", usage=Usage(input_tokens=190_000)),
                ProviderResponse(text="summary of earlier turns"),
                ProviderResponse(text="reply-3", usage=Usage(input_tokens=1_000)),
            ]
        )
        provider.model = "claude-sonnet-5"
        events = []
        agent = Agent(
            provider=provider,
            on_compact_start=lambda: events.append("start"),
            on_compact_end=lambda before, after: events.append((before, after)),
        )
        session = Session(system_prompt="sys")

        agent.run("first", session=session)
        agent.run("second", session=session)
        agent.run("third", session=session)

        self.assertEqual(events, ["start", (5, 4)])
        self.assertEqual(session.messages[0].role, "assistant")
        self.assertIn("summary of earlier turns", session.messages[0].content)
        self.assertEqual(len(session.messages), 5)

    def test_auto_compact_false_never_compacts(self):
        provider = FakeProvider(
            [
                ProviderResponse(text="reply-1", usage=Usage(input_tokens=190_000)),
                ProviderResponse(text="reply-2", usage=Usage(input_tokens=190_000)),
                ProviderResponse(text="reply-3", usage=Usage(input_tokens=190_000)),
            ]
        )
        provider.model = "claude-sonnet-5"
        agent = Agent(provider=provider, auto_compact=False)
        session = Session(system_prompt="sys")

        agent.run("first", session=session)
        agent.run("second", session=session)
        agent.run("third", session=session)

        self.assertEqual(len(session.messages), 6)

    def test_cancel_event_stops_before_the_next_provider_call(self):
        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[ToolCall(id="1", name="echo", arguments={"text": "a"})],
                ),
                ProviderResponse(text="should never be reached"),
            ]
        )
        cancel_event = threading.Event()

        class CancellingEchoTool(EchoTool):
            def run(self, text: str) -> ToolResult:
                cancel_event.set()
                return super().run(text)

        agent = Agent(provider=provider, tools=[CancellingEchoTool()])
        session = Session(system_prompt="sys")

        result = agent.run("go", session=session, cancel_event=cancel_event)

        self.assertEqual(result, "Cancelled by user.")
        self.assertEqual(len(provider._scripted), 1)  # 2nd response never consumed
        roles = [m.role for m in session.messages]
        self.assertEqual(roles, ["user", "assistant", "tool"])

    def test_cancel_event_set_before_run_returns_immediately(self):
        provider = FakeProvider([ProviderResponse(text="should never be reached")])
        cancel_event = threading.Event()
        cancel_event.set()
        agent = Agent(provider=provider)

        result = agent.run("go", cancel_event=cancel_event)

        self.assertEqual(result, "Cancelled by user.")
        self.assertEqual(len(provider._scripted), 1)


class FlakyProvider(Provider):
    """Raises a retryable error `fail_times` times, then succeeds."""

    name = "flaky"

    def __init__(self, fail_times: int, status_code: int = 429) -> None:
        super().__init__(model="fake-model")
        self.fail_times = fail_times
        self.status_code = status_code
        self.calls = 0

    def complete(
        self, system_prompt, messages, tools, on_delta=None
    ) -> ProviderResponse:
        self.calls += 1
        if self.calls <= self.fail_times:
            exc = Exception(f"failed attempt {self.calls}")
            exc.status_code = self.status_code
            raise exc
        return ProviderResponse(text="ok")


class TestAgentRetry(unittest.TestCase):
    def setUp(self):
        import pycodeloop.core.agent as agent_module

        patcher = mock.patch.object(agent_module.time, "sleep")
        self.mock_sleep = patcher.start()
        self.addCleanup(patcher.stop)

    def test_retries_retryable_errors_and_eventually_succeeds(self):
        provider = FlakyProvider(fail_times=2)
        events = []
        agent = Agent(
            provider=provider,
            tools=[],
            on_retry=lambda attempt, delay, exc: events.append((attempt, delay)),
        )

        result = agent.run("hi")

        self.assertEqual(result, "ok")
        self.assertEqual(provider.calls, 3)
        self.assertEqual(events, [(1, 1.0), (2, 2.0)])

    def test_gives_up_after_max_retries(self):
        provider = FlakyProvider(fail_times=10)
        agent = Agent(provider=provider, tools=[])

        with self.assertRaises(Exception):
            agent.run("hi")

        self.assertEqual(provider.calls, 4)  # 1 initial + 3 retries

    def test_non_retryable_error_raises_immediately(self):
        provider = FlakyProvider(fail_times=1, status_code=400)
        agent = Agent(provider=provider, tools=[])

        with self.assertRaises(Exception):
            agent.run("hi")

        self.assertEqual(provider.calls, 1)


class TestAgentParallelTools(unittest.TestCase):
    def test_independent_safe_tools_run_concurrently(self):
        barrier = threading.Barrier(2, timeout=2)

        class BarrierTool(Tool):
            name = "barrier"
            description = "waits at a barrier to prove concurrency"
            parameters = {
                "type": "object",
                "properties": {"id": {"type": "string"}},
            }

            def run(self, id: str) -> ToolResult:
                barrier.wait()
                return ToolResult(output=f"done {id}")

        class BarrierTool2(BarrierTool):
            name = "barrier2"

        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[
                        ToolCall(id="1", name="barrier", arguments={"id": "a"}),
                        ToolCall(id="2", name="barrier2", arguments={"id": "b"}),
                    ],
                ),
                ProviderResponse(text="done"),
            ]
        )
        agent = Agent(provider=provider, tools=[BarrierTool(), BarrierTool2()])

        result = agent.run("go")

        self.assertEqual(result, "done")

    def test_dangerous_tool_in_batch_forces_sequential_and_confirms(self):
        class SafeTool(Tool):
            name = "safe"
            description = "safe"
            parameters = {"type": "object", "properties": {}}

            def run(self) -> ToolResult:
                return ToolResult(output="safe done")

        class DangerTool(Tool):
            name = "danger"
            description = "danger"
            parameters = {"type": "object", "properties": {}}
            dangerous = True

            def run(self) -> ToolResult:
                return ToolResult(output="danger done")

        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[
                        ToolCall(id="1", name="safe", arguments={}),
                        ToolCall(id="2", name="danger", arguments={}),
                    ],
                ),
                ProviderResponse(text="done"),
            ]
        )
        confirmed = []
        agent = Agent(
            provider=provider,
            tools=[SafeTool(), DangerTool()],
            confirm=lambda name, preview: confirmed.append(name) or True,
        )

        agent.run("go")

        self.assertEqual(confirmed, ["danger"])

    def test_repeated_tool_name_in_batch_runs_sequential(self):
        calls_seen = []

        class RecordingTool(Tool):
            name = "rec"
            description = "records call order, not thread-safe"
            parameters = {"type": "object", "properties": {"n": {"type": "string"}}}

            def run(self, n: str) -> ToolResult:
                calls_seen.append(n)
                return ToolResult(output=f"ok {n}")

        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[
                        ToolCall(id="1", name="rec", arguments={"n": "1"}),
                        ToolCall(id="2", name="rec", arguments={"n": "2"}),
                    ],
                ),
                ProviderResponse(text="done"),
            ]
        )
        agent = Agent(provider=provider, tools=[RecordingTool()])

        agent.run("go")

        self.assertEqual(calls_seen, ["1", "2"])


if __name__ == "__main__":
    unittest.main()
