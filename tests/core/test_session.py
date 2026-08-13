"""Test Session.trim()"""

import unittest

from pycodeloop.core.session import Message, Session


def _add_turn(session: Session, user_text: str, assistant_text: str) -> None:
    session.add_user(user_text)
    session.add_assistant(assistant_text)


class TestSessionTrim(unittest.TestCase):
    def test_trim_keeps_last_n_turns(self):
        session = Session(system_prompt="sys")
        for i in range(5):
            _add_turn(session, f"user-{i}", f"assistant-{i}")

        session.trim(max_turns=2)

        self.assertEqual(len(session.messages), 4)
        self.assertEqual(session.messages[0].content, "user-3")
        self.assertEqual(session.messages[-1].content, "assistant-4")

    def test_trim_is_a_noop_when_under_the_cap(self):
        session = Session(system_prompt="sys")
        for i in range(2):
            _add_turn(session, f"user-{i}", f"assistant-{i}")

        session.trim(max_turns=5)

        self.assertEqual(len(session.messages), 4)

    def test_trim_never_splits_a_tool_call_tool_result_pair(self):
        session = Session(system_prompt="sys")
        _add_turn(session, "user-0", "assistant-0")
        session.add_user("user-1")
        session.add_assistant(
            "", tool_calls=[{"id": "c1", "name": "bash", "arguments": {}}]
        )
        session.add_tool_result("c1", "output")
        session.add_assistant("final")

        session.trim(max_turns=1)

        # Only the "user-1" turn survives, with its assistant/tool_result
        # messages intact — never truncated mid-turn.
        self.assertEqual(session.messages[0].content, "user-1")
        roles = [m.role for m in session.messages]
        self.assertEqual(roles, ["user", "assistant", "tool", "assistant"])


class TestSessionRepairsDanglingToolCalls(unittest.TestCase):
    def test_history_fills_in_missing_tool_results(self):
        session = Session(system_prompt="sys")
        session.add_user("do the thing")
        session.add_assistant(
            "",
            tool_calls=[
                {"id": "c1", "name": "bash", "arguments": {}},
                {"id": "c2", "name": "read_file", "arguments": {}},
            ],
        )
        # No add_tool_result() calls — simulates the process dying right
        # after the assistant's tool_use message was persisted.

        history = session.history()

        roles = [m.role for m in history]
        self.assertEqual(roles, ["user", "assistant", "tool", "tool"])
        self.assertEqual(history[2].tool_call_id, "c1")
        self.assertEqual(history[3].tool_call_id, "c2")

    def test_history_is_idempotent_after_repair(self):
        session = Session(system_prompt="sys")
        session.add_user("do the thing")
        session.add_assistant(
            "", tool_calls=[{"id": "c1", "name": "bash", "arguments": {}}]
        )

        session.history()
        second_call = session.history()

        self.assertEqual(len(second_call), 3)

    def test_history_leaves_a_complete_session_untouched(self):
        session = Session(system_prompt="sys")
        session.add_user("do the thing")
        session.add_assistant(
            "", tool_calls=[{"id": "c1", "name": "bash", "arguments": {}}]
        )
        session.add_tool_result("c1", "output")

        history = session.history()

        self.assertEqual(len(history), 3)
        self.assertEqual(history[-1].content, "output")


class TestSessionImages(unittest.TestCase):
    def test_add_user_without_images_leaves_images_none(self):
        session = Session(system_prompt="sys")
        session.add_user("hi")

        self.assertIsNone(session.messages[0].images)

    def test_add_user_with_images_stores_them_on_the_message(self):
        session = Session(system_prompt="sys")
        session.add_user("what is this?", images=["base64-a", "base64-b"])

        message = session.messages[0]
        self.assertEqual(message.role, "user")
        self.assertEqual(message.images, ["base64-a", "base64-b"])

    def test_message_images_defaults_to_none(self):
        message = Message(role="user", content="hi")

        self.assertIsNone(message.images)


if __name__ == "__main__":
    unittest.main()
