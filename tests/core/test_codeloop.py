"""Test CodeLoop's session_key/storage wiring"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from codeloop.abc.provider import Provider, ProviderResponse
from codeloop.core import codeloop as codeloop_module
from codeloop.core.codeloop import CodeLoop
from codeloop.core.config import Config
from codeloop.core.persistence import sessions as sessions_module
from codeloop.core.persistence.local_config import JsonFileStore
from codeloop.core.persistence.sessions import FileSessions
from codeloop.core.persistence.usage import UsageTracker


class FakeProvider(Provider):
    name = "fake"

    def __init__(self, scripted: list[ProviderResponse]) -> None:
        super().__init__(model="fake-model")
        self._scripted = list(scripted)

    def complete(
        self, system_prompt, messages, tools, on_delta=None
    ) -> ProviderResponse:
        return self._scripted.pop(0)


class TestCodeLoopSessionStorage(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.storage = FileSessions(directory=Path(self._tmpdir.name))

        # FileSessions' session index and usage tracking both write to
        # ~/.codeloop/config.json — redirect that to a scratch file so
        # tests never touch the real user config.
        store = JsonFileStore(Path(self._tmpdir.name) / "config.json")

        sessions_patcher = mock.patch.object(sessions_module, "default_store", store)
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
        )
        flow = CodeLoop(config=config)

        flow.run("hello")

        self.assertIsNone(self.storage.get("anything"))

    def test_run_with_session_key_persists_session(self):
        config = Config(
            provider=FakeProvider([ProviderResponse(text="hi")]),
            storage=self.storage,
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
        )
        flow = CodeLoop(config=config)
        flow.run("hello", session_key="s1")

        # A fresh CodeLoop instance (e.g. a new process) picks up the
        # same session via the shared storage + key.
        config2 = Config(
            provider=FakeProvider([ProviderResponse(text="second")]),
            storage=self.storage,
        )
        flow2 = CodeLoop(config=config2)
        flow2.run("again", session_key="s1")

        stored = self.storage.get("s1")
        # 2 messages from the first run + 2 from the second
        self.assertEqual(len(stored.messages), 4)


if __name__ == "__main__":
    unittest.main()
