"""Functional: real HTTP socket + real Agent + real SQLite-backed
session storage — a session persisted by one `CodeLoop` instance must
resume correctly in a brand-new instance pointed at the same file."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pycodeloop.core.codeloop import CodeLoop
from pycodeloop.core.config import Config
from pycodeloop.store.sqlite_sessions import SqliteSessions
from pycodeloop.providers.generic import GenericProvider
from tests.functional._fake_llm_server import FakeLLMServer, chat_completion


class TestCodeLoopPersistenceEndToEnd(unittest.TestCase):
    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.db_path = Path(tmpdir.name) / "sessions.db"

    def _codeloop(self, responses: list[dict]) -> tuple[CodeLoop, FakeLLMServer]:
        server = FakeLLMServer(responses)
        self.addCleanup(server.close)
        provider = GenericProvider(url=server.url, model="test-model")
        config = Config(
            provider=provider,
            tools=[],
            storage=SqliteSessions(path=self.db_path),
        )
        return CodeLoop(config=config), server

    def test_second_process_resumes_history_from_the_first(self):
        flow_one, _server_one = self._codeloop([chat_completion(text="hi there")])
        flow_one.run("hello", session_key="conversation-1")

        flow_two, server_two = self._codeloop([chat_completion(text="I remember you")])
        flow_two.run("do you remember me?", session_key="conversation-1")

        sent_messages = server_two.requests[0]["messages"]
        user_turns = [m["content"] for m in sent_messages if m["role"] == "user"]
        self.assertIn("hello", user_turns)
        self.assertIn("do you remember me?", user_turns)

    def test_different_session_keys_stay_isolated(self):
        flow, server = self._codeloop(
            [chat_completion(text="reply-a"), chat_completion(text="reply-b")]
        )

        flow.run("message for a", session_key="session-a")
        flow.run("message for b", session_key="session-b")

        second_request_messages = server.requests[1]["messages"]
        user_turns = [
            m["content"] for m in second_request_messages if m["role"] == "user"
        ]
        self.assertEqual(user_turns, ["message for b"])


if __name__ == "__main__":
    unittest.main()
