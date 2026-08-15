"""Test SqliteSessions"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sqlalchemy import text
from sqlalchemy.orm import Query

from pycodeloop.core.session import Message, Session
from pycodeloop.store.sqlite_sessions import SqliteSessions


class TestSqliteSessions(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.sessions = SqliteSessions(
            path=Path(self._tmpdir.name) / "sessions.db"
        )

    def _post_and_spy_on_delete(self, key: str, session: Session) -> bool:
        """Posts `session` and returns whether the message table's
        delete-and-reinsert path ran, by spying on `Query.delete` —
        the only place `post()` deletes existing `MessageRecord` rows."""
        with mock.patch.object(
            Query, "delete", autospec=True, side_effect=Query.delete
        ) as spy:
            self.sessions.post(key, session)
        return spy.called

    def _row_ids(self, key: str) -> list[int]:
        with self.sessions._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id FROM messages WHERE session_key = :key "
                    "ORDER BY position"
                ),
                {"key": key},
            ).fetchall()
        return [row[0] for row in rows]

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
        self.assertEqual(
            restored.messages[0], Message(role="user", content="hi")
        )

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

    def test_post_appends_incrementally_without_rewriting_existing_rows(
        self,
    ):
        session = Session(system_prompt="sys")
        session.add_user("hi")
        session.add_assistant("hello")
        self.sessions.post("s1", session)
        original_ids = self._row_ids("s1")

        session.add_tool_result("call-1", "ok")
        did_rewrite = self._post_and_spy_on_delete("s1", session)

        self.assertFalse(did_rewrite)
        new_ids = self._row_ids("s1")
        self.assertEqual(new_ids[: len(original_ids)], original_ids)
        self.assertEqual(len(new_ids), len(original_ids) + 1)

        restored = self.sessions.get("s1")
        self.assertEqual(len(restored.messages), 3)
        self.assertEqual(restored.messages[2].content, "ok")

    def test_post_does_a_full_rewrite_when_the_session_is_marked_dirty(self):
        session = Session(system_prompt="sys")
        session.add_user("hi")
        session.add_assistant("hello")
        self.sessions.post("s1", session)

        session.replace_messages([Message(role="user", content="summary")])
        did_rewrite = self._post_and_spy_on_delete("s1", session)

        self.assertTrue(did_rewrite)
        restored = self.sessions.get("s1")
        self.assertEqual(len(restored.messages), 1)
        self.assertEqual(restored.messages[0].content, "summary")

    def test_post_does_a_full_rewrite_for_a_different_session_object(self):
        first = Session(system_prompt="sys")
        first.add_user("first")
        self.sessions.post("s1", first)

        second = Session(system_prompt="sys")
        second.add_user("second")
        did_rewrite = self._post_and_spy_on_delete("s1", second)

        self.assertTrue(did_rewrite)

    def test_creates_db_file_and_parent_dir(self):
        nested = Path(self._tmpdir.name) / "nested" / "sessions.db"
        SqliteSessions(path=nested)

        self.assertTrue(nested.exists())


if __name__ == "__main__":
    unittest.main()
