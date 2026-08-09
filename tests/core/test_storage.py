"""Test Storage ABC and FileStorage"""

import tempfile
import unittest
from pathlib import Path

from codeloop.core.session import Message, Session
from codeloop.core.storage import FileStorage


class TestFileStorage(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.storage = FileStorage(directory=Path(self._tmpdir.name))

    def test_post_then_get_roundtrips_session(self):
        session = Session(system_prompt="sys", cwd="/tmp")
        session.add_user("hi")
        session.add_assistant("hello", tool_calls=None)
        session.add_tool_result("call-1", "ok")

        self.storage.post("s1", session)
        restored = self.storage.get("s1")

        self.assertIsNotNone(restored)
        self.assertEqual(restored.system_prompt, "sys")
        self.assertEqual(restored.cwd, "/tmp")
        self.assertEqual(len(restored.messages), 3)
        self.assertEqual(restored.messages[0], Message(role="user", content="hi"))

    def test_get_missing_key_returns_none(self):
        self.assertIsNone(self.storage.get("nope"))

    def test_delete_removes_stored_session(self):
        session = Session(system_prompt="sys")
        self.storage.post("s1", session)

        self.storage.delete("s1")

        self.assertIsNone(self.storage.get("s1"))

    def test_delete_missing_key_is_a_noop(self):
        self.storage.delete("nope")  # should not raise


if __name__ == "__main__":
    unittest.main()
