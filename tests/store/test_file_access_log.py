"""Test FileAccessLog"""

import tempfile
import unittest
from pathlib import Path

from pycodeloop.store.file_access_log import (
    FileAccessLog,
    current_session_key,
    session_scope,
)


class TestFileAccessLog(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.log = FileAccessLog(path=Path(self._tmpdir.name) / "access.db")

    def test_last_record_returns_none_when_never_accessed(self):
        self.assertIsNone(self.log.last_record("a.py"))

    def test_last_record_returns_the_most_recent_entry(self):
        self.log.record("a.py", "read", content_hash="h1", session_key="s1")
        self.log.record("a.py", "write", content_hash="h2", session_key="s1")

        last = self.log.last_record("a.py", session_key="s1")

        self.assertEqual(last.action, "write")
        self.assertEqual(last.content_hash, "h2")

    def test_records_are_scoped_by_session(self):
        self.log.record("a.py", "read", content_hash="h1", session_key="s1")

        self.assertIsNone(self.log.last_record("a.py", session_key="s2"))

    def test_history_lists_records_newest_first(self):
        self.log.record("a.py", "read", session_key="s1")
        self.log.record("b.py", "write", session_key="s1")

        history = self.log.history("s1")

        self.assertEqual([r.path for r in history], ["b.py", "a.py"])

    def test_creates_db_file_and_parent_dir(self):
        path = Path(self._tmpdir.name) / "nested" / "access.db"
        FileAccessLog(path=path)

        self.assertTrue(path.exists())


class TestSessionScope(unittest.TestCase):
    def test_defaults_to_global_outside_any_scope(self):
        self.assertEqual(current_session_key(), "global")

    def test_binds_the_session_key_for_the_duration_of_the_block(self):
        with session_scope("my-session"):
            self.assertEqual(current_session_key(), "my-session")

        self.assertEqual(current_session_key(), "global")


if __name__ == "__main__":
    unittest.main()
