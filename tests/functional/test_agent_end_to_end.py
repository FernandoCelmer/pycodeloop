"""Functional: real HTTP socket + real Agent tool-use loop + real
filesystem — nothing mocked below `Agent`."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pycodeloop.core.agent import Agent
from pycodeloop.providers.generic import GenericProvider
from pycodeloop.store.file_access_log import FileAccessLog
from pycodeloop.tools.filesystem import ReadFileTool, WriteFileTool
from tests.functional._fake_llm_server import (
    FakeLLMServer,
    chat_completion,
    tool_call,
)


class AgentEndToEndTestCase(unittest.TestCase):
    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.tmp_path = Path(tmpdir.name).resolve()

        previous_cwd = os.getcwd()
        os.chdir(self.tmp_path)
        self.addCleanup(os.chdir, previous_cwd)

        logdir = tempfile.TemporaryDirectory()
        self.addCleanup(logdir.cleanup)
        patcher = mock.patch(
            "pycodeloop.tools.filesystem.default_log",
            FileAccessLog(path=Path(logdir.name) / "access.db"),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.server: FakeLLMServer | None = None
        self.addCleanup(self._close_server)

    def _close_server(self) -> None:
        if self.server is not None:
            self.server.close()

    def _provider(self, responses: list[dict]) -> GenericProvider:
        self.server = FakeLLMServer(responses)
        return GenericProvider(url=self.server.url, model="test-model")


class TestToolUseLoop(AgentEndToEndTestCase):
    def test_write_then_read_file_over_real_http_and_filesystem(self):
        provider = self._provider(
            [
                chat_completion(
                    tool_calls=[
                        tool_call(
                            "call-1",
                            "write_file",
                            {
                                "path": "note.txt",
                                "content": "hello from the model",
                            },
                        )
                    ]
                ),
                chat_completion(text="Done — wrote note.txt."),
            ]
        )
        agent = Agent(
            provider=provider,
            tools=[WriteFileTool(), ReadFileTool()],
            confirm=lambda *args: True,
        )

        result = agent.run("write a note")

        self.assertEqual(result, "Done — wrote note.txt.")
        self.assertEqual(
            (self.tmp_path / "note.txt").read_text(), "hello from the model"
        )
        self.assertEqual(len(self.server.requests), 2)

    def test_tool_result_is_fed_back_into_the_next_request(self):
        (self.tmp_path / "existing.txt").write_text("42")
        provider = self._provider(
            [
                chat_completion(
                    tool_calls=[
                        tool_call(
                            "call-1", "read_file", {"path": "existing.txt"}
                        )
                    ]
                ),
                chat_completion(text="The file contains 42."),
            ]
        )
        agent = Agent(
            provider=provider,
            tools=[ReadFileTool()],
            confirm=lambda *args: True,
        )

        result = agent.run("what's in existing.txt?")

        self.assertEqual(result, "The file contains 42.")
        second_request = self.server.requests[1]
        tool_messages = [
            m for m in second_request["messages"] if m["role"] == "tool"
        ]
        self.assertEqual(len(tool_messages), 1)
        self.assertIn("42", tool_messages[0]["content"])

    def test_declining_a_dangerous_tool_is_reported_back_to_the_model(self):
        provider = self._provider(
            [
                chat_completion(
                    tool_calls=[
                        tool_call(
                            "call-1",
                            "write_file",
                            {"path": "x.txt", "content": "x"},
                        )
                    ]
                ),
                chat_completion(text="Okay, skipped."),
            ]
        )
        agent = Agent(
            provider=provider,
            tools=[WriteFileTool()],
            confirm=lambda *args: False,
        )

        result = agent.run("write x.txt")

        self.assertEqual(result, "Okay, skipped.")
        self.assertFalse((self.tmp_path / "x.txt").exists())


if __name__ == "__main__":
    unittest.main()
