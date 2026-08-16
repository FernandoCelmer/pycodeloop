"""Test CodeLoop's session_key/storage wiring"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pycodeloop.abc.provider import Provider, ProviderResponse, ToolCall
from pycodeloop.abc.tool import Tool, ToolResult
from pycodeloop.core import codeloop as codeloop_module
from pycodeloop.core.codeloop import CodeLoop
from pycodeloop.core.config import Config
from pycodeloop.store import file_sessions as sessions_module
from pycodeloop.store.execution_trace import JsonlTracer
from pycodeloop.store.file_sessions import FileSessions
from pycodeloop.store.json_store import JsonFileStore
from pycodeloop.store.usage_tracker import UsageTracker


class FakeProvider(Provider):
    name = "fake"

    def __init__(self, scripted: list[ProviderResponse]) -> None:
        super().__init__(model="fake-model")
        self._scripted = list(scripted)

    def complete(
        self, system_prompt, messages, tools, on_delta=None, cancel_event=None
    ) -> ProviderResponse:
        return self._scripted.pop(0)


class EchoTool(Tool):
    name = "echo"
    description = "echoes"
    parameters = {"type": "object", "properties": {"x": {"type": "string"}}}

    def run(self, x: str = "") -> ToolResult:
        return ToolResult(output=f"echoed {x}")


class TestCodeLoopSessionStorage(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.storage = FileSessions(directory=Path(self._tmpdir.name))

        # FileSessions' session index and usage tracking both write to
        # ~/.pycodeloop/config.json — redirect that to a scratch file so
        # tests never touch the real user config.
        store = JsonFileStore(Path(self._tmpdir.name) / "config.json")

        sessions_patcher = mock.patch.object(
            sessions_module, "default_store", store
        )
        sessions_patcher.start()
        self.addCleanup(sessions_patcher.stop)

        usage_patcher = mock.patch.object(
            codeloop_module, "_usage_tracker", UsageTracker(store=store)
        )
        usage_patcher.start()
        self.addCleanup(usage_patcher.stop)

    def test_run_without_session_key_never_touches_storage(self):
        config = Config(
            provider=FakeProvider([ProviderResponse(text="hi")]),
            storage=self.storage,
            trace=False,
        )
        flow = CodeLoop(config=config)

        flow.run("hello")

        self.assertIsNone(self.storage.get("anything"))

    def test_run_with_session_key_persists_session(self):
        config = Config(
            provider=FakeProvider([ProviderResponse(text="hi")]),
            storage=self.storage,
            trace=False,
        )
        flow = CodeLoop(config=config)

        flow.run("hello", session_key="s1")

        stored = self.storage.get("s1")
        self.assertIsNotNone(stored)
        self.assertEqual(len(stored.messages), 2)  # user + assistant

    def test_run_resumes_a_previously_stored_session(self):
        config = Config(
            provider=FakeProvider([ProviderResponse(text="first")]),
            storage=self.storage,
            trace=False,
        )
        flow = CodeLoop(config=config)
        flow.run("hello", session_key="s1")

        # A fresh CodeLoop instance (e.g. a new process) picks up the
        # same session via the shared storage + key.
        config2 = Config(
            provider=FakeProvider([ProviderResponse(text="second")]),
            storage=self.storage,
            trace=False,
        )
        flow2 = CodeLoop(config=config2)
        flow2.run("again", session_key="s1")

        stored = self.storage.get("s1")
        # 2 messages from the first run + 2 from the second
        self.assertEqual(len(stored.messages), 4)

    def test_run_persists_incrementally_not_only_at_the_end(self):
        """A crash mid-turn (e.g. during a long tool-call sequence)
        shouldn't lose everything the turn already did — each message
        must hit storage as it's added, not only after run() returns."""
        provider = FakeProvider(
            [
                ProviderResponse(
                    text="",
                    tool_calls=[
                        ToolCall(id="1", name="echo", arguments={"x": "a"})
                    ],
                ),
                ProviderResponse(text="all done"),
            ]
        )
        config = Config(
            provider=provider,
            storage=self.storage,
            tools=[EchoTool()],
            trace=False,
        )
        flow = CodeLoop(config=config)

        seen_counts = []
        original_post = self.storage.post

        def spy_post(key, session):
            seen_counts.append(len(session.messages))
            original_post(key, session)

        with mock.patch.object(self.storage, "post", side_effect=spy_post):
            flow.run("hello", session_key="s1")

        # user, assistant(tool_calls), tool_result, assistant(final), plus
        # CodeLoop's own end-of-run save (redundant but harmless) — each
        # save sees one more message than the last, not a single jump
        # straight to the final count.
        self.assertEqual(seen_counts, [1, 2, 3, 4, 4])


class TestCodeLoopTrace(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.logs_dir = Path(self._tmpdir.name) / "logs"

        patcher = mock.patch.object(
            codeloop_module,
            "JsonlTracer",
            side_effect=lambda session_key: JsonlTracer(
                session_key, directory=self.logs_dir
            ),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_trace_on_by_default_writes_run_and_turn_events(self):
        config = Config(
            provider=FakeProvider([ProviderResponse(text="hi")]),
            storage=False,
        )
        flow = CodeLoop(config=config)

        flow.run("hello", session_key="s1")

        lines = (self.logs_dir / "s1.jsonl").read_text().splitlines()
        types = [json.loads(line)["type"] for line in lines]
        self.assertEqual(types, ["run_start", "turn", "run_end"])

    def test_trace_false_writes_nothing(self):
        config = Config(
            provider=FakeProvider([ProviderResponse(text="hi")]),
            storage=False,
            trace=False,
        )
        flow = CodeLoop(config=config)

        flow.run("hello", session_key="s1")

        self.assertFalse((self.logs_dir / "s1.jsonl").exists())

    def test_trace_without_session_key_uses_global_file(self):
        config = Config(
            provider=FakeProvider([ProviderResponse(text="hi")]),
            storage=False,
        )
        flow = CodeLoop(config=config)

        flow.run("hello")

        self.assertTrue((self.logs_dir / "global.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
