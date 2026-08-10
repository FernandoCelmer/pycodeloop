"""Test CodeLoopApp's slash-command handling and confirm-queue staleness
(unit-level, without spinning up the full Textual app)."""

import time
import unittest
from types import SimpleNamespace
from unittest import mock

from pycodeloop.cli.tui import CodeLoopApp


def _fake_app(model="claude-sonnet-5", reloadable=False):
    provider = SimpleNamespace(model=model)
    if reloadable:
        provider.reload = mock.Mock(
            side_effect=lambda: setattr(provider, "model", "reloaded-model")
        )
    flow = SimpleNamespace(agent=SimpleNamespace(provider=provider))
    app = CodeLoopApp(flow, "generic", model)
    app._log = mock.Mock()
    app.call_from_thread = lambda fn, *a, **k: fn(*a, **k)
    return app


class TestHandleCommand(unittest.TestCase):
    def test_not_a_command_returns_false(self):
        app = _fake_app()

        self.assertFalse(app._handle_command("hello there"))

    def test_model_alone_reports_current_model(self):
        app = _fake_app(model="claude-sonnet-5")

        self.assertTrue(app._handle_command("/model"))
        self.assertEqual(app.flow.agent.provider.model, "claude-sonnet-5")

    def test_model_with_arg_switches_model_and_subtitle(self):
        app = _fake_app(model="claude-sonnet-5")

        self.assertTrue(app._handle_command("/model gpt-5"))

        self.assertEqual(app.flow.agent.provider.model, "gpt-5")
        self.assertEqual(app.model_name, "gpt-5")
        self.assertIn("gpt-5", app.sub_title)

    def test_reload_calls_provider_reload(self):
        app = _fake_app(model="old-model", reloadable=True)

        self.assertTrue(app._handle_command("/reload"))

        app.flow.agent.provider.reload.assert_called_once()
        self.assertEqual(app.model_name, "reloaded-model")

    def test_reload_without_support_is_a_noop(self):
        app = _fake_app(reloadable=False)

        self.assertTrue(app._handle_command("/reload"))


class TestConfirmStaleness(unittest.TestCase):
    def test_timeout_auto_confirms_and_marks_stale(self):
        app = _fake_app()
        app.CONFIRM_TIMEOUT = 0.05

        result = app._confirm("bash", "$ echo hi")

        self.assertTrue(result)
        self.assertTrue(app._stale_confirm_answer)

    def test_late_answer_does_not_leak_into_next_confirm(self):
        app = _fake_app()
        app.CONFIRM_TIMEOUT = 0.05

        first = app._confirm("bash", "$ echo a")
        self.assertTrue(first)

        # Late answer for the first prompt arrives after its timeout,
        # before a second confirm gets a chance to ask.
        app._confirm_queue.put("n")

        second = app._confirm("bash", "$ echo b")

        self.assertTrue(
            second,
            "stale answer from the first prompt leaked into the second "
            "confirm instead of being drained",
        )

    def test_plain_answer_still_works_normally(self):
        app = _fake_app()
        app._confirm_queue.put("n")

        result = app._confirm("bash", "$ echo hi")

        self.assertFalse(result)

    def test_freeform_text_answer_is_returned_as_redirect(self):
        app = _fake_app()
        app._confirm_queue.put("use ls instead")

        result = app._confirm("bash", "$ rm -rf /tmp/x")

        self.assertEqual(result, "use ls instead")

    def test_expired_stale_flag_is_not_drained_forever(self):
        app = _fake_app()
        app._stale_confirm_answer = True
        app._stale_expires_at = time.monotonic() - 1  # already expired

        app._drain_stale_confirm_answer()

        self.assertFalse(app._stale_confirm_answer)


if __name__ == "__main__":
    unittest.main()
