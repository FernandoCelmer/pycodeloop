"""Test CodeLoop's session_key/storage wiring"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from codeloop.abc.provider import Provider, ProviderResponse
from codeloop.core import local_config
from codeloop.core.codeloop import CodeLoop
from codeloop.core.config import Config
from codeloop.core.storage import FileStorage


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
        self.storage = FileStorage(directory=Path(self._tmpdir.name))

        # record_usage()/FileStorage's session index both write to
        # ~/.codeloop/config.json via local_config — redirect that to a
        # scratch file so tests never touch the real user config.
        patcher = mock.patch.object(
            local_config, "CONFIG_PATH", Path(self._tmpdir.name) / "config.json"
        )
        patcher.start()
        self.addCleanup(patcher.stop)

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
