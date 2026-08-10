"""Test Sessions ABC and FileSessions"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pycodeloop.core.persistence import sessions as sessions_module
from pycodeloop.core.persistence.local_config import JsonFileStore
from pycodeloop.core.persistence.sessions import FileSessions
from pycodeloop.core.session import Message, Session


class TestFileSessions(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.sessions = FileSessions(directory=Path(self._tmpdir.name))

        # post()/delete() also write a session index entry to
        # ~/.pycodeloop/config.json — redirect that to a scratch file.
        store = JsonFileStore(Path(self._tmpdir.name) / "config.json")
        patcher = mock.patch.object(sessions_module, "default_store", store)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_post_then_get_roundtrips_session(self):
        session = Session(system_prompt="sys", cwd="/tmp")
        session.add_user("hi")
        session.add_assistant("hello", tool_calls=None)
        session.add_tool_result("call-1", "ok")

        self.sessions.post("s1", session)
        restored = self.sessions.get("s1")

        self.assertIsNotNone(restored)
        self.assertEqual(restored.system_prompt, "sys")
        self.assertEqual(restored.cwd, "/tmp")
        self.assertEqual(len(restored.messages), 3)
        self.assertEqual(restored.messages[0], Message(role="user", content="hi"))

    def test_get_missing_key_returns_none(self):
        self.assertIsNone(self.sessions.get("nope"))

    def test_delete_removes_stored_session(self):
        session = Session(system_prompt="sys")
        self.sessions.post("s1", session)

        self.sessions.delete("s1")

        self.assertIsNone(self.sessions.get("s1"))

    def test_delete_missing_key_is_a_noop(self):
        self.sessions.delete("nope")  # should not raise

    def test_post_indexes_session_for_list_sessions(self):
        session = Session(system_prompt="sys", cwd="/tmp/proj")
        session.add_user("hi")
        session.add_assistant("hello")

        self.sessions.post("s1", session)

        index = FileSessions.list_sessions()
        self.assertIn("s1", index)
        self.assertEqual(index["s1"]["message_count"], 2)
        self.assertEqual(index["s1"]["cwd"], "/tmp/proj")

    def test_delete_removes_session_from_index(self):
        session = Session(system_prompt="sys")
        self.sessions.post("s1", session)

        self.sessions.delete("s1")

        self.assertNotIn("s1", FileSessions.list_sessions())


if __name__ == "__main__":
    unittest.main()
