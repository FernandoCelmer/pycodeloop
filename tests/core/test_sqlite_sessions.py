"""Test SqliteSessions"""

import tempfile
import unittest
from pathlib import Path

from pycodeloop.core.store.sqlite_sessions import SqliteSessions
from pycodeloop.core.session import Message, Session


class TestSqliteSessions(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.sessions = SqliteSessions(path=Path(self._tmpdir.name) / "sessions.db")

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

    def test_post_overwrites_existing_key(self):
        first = Session(system_prompt="sys")
        first.add_user("first")
        self.sessions.post("s1", first)

        second = Session(system_prompt="sys")
        second.add_user("second")
        second.add_assistant("reply")
        self.sessions.post("s1", second)

        restored = self.sessions.get("s1")
        self.assertEqual(len(restored.messages), 2)
        self.assertEqual(restored.messages[0].content, "second")

    def test_delete_removes_stored_session(self):
        session = Session(system_prompt="sys")
        self.sessions.post("s1", session)

        self.sessions.delete("s1")

        self.assertIsNone(self.sessions.get("s1"))

    def test_delete_missing_key_is_a_noop(self):
        self.sessions.delete("nope")  # should not raise

    def test_list_sessions_returns_index(self):
        session = Session(system_prompt="sys", cwd="/tmp/proj")
        session.add_user("hi")
        session.add_assistant("hello")
        self.sessions.post("s1", session)

        index = self.sessions.list_sessions()

        self.assertIn("s1", index)
        self.assertEqual(index["s1"]["message_count"], 2)
        self.assertEqual(index["s1"]["cwd"], "/tmp/proj")

    def test_creates_db_file_and_parent_dir(self):
        nested = Path(self._tmpdir.name) / "nested" / "sessions.db"
        SqliteSessions(path=nested)

        self.assertTrue(nested.exists())


if __name__ == "__main__":
    unittest.main()
