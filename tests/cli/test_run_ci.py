"""Functional: `pycodeloop run --ci/--output json` exit codes and JSON."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from typer.testing import CliRunner

from pycodeloop.cli.main import app
from pycodeloop.cli.render import console
from pycodeloop.store.execution_trace import JsonlTracer
from pycodeloop.store.file_access_log import (
    default_log as file_access_singleton,
)
from pycodeloop.store.sqlite_sessions import SqliteSessions
from tests.functional._fake_llm_server import (
    FakeLLMServer,
    chat_completion,
    tool_call,
)


class TestRunCommandCI(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        self._cwd = os.getcwd()
        os.chdir(self.tmp)

        # The file-access tools capture the `default_log` singleton at
        # construction time, so point that one shared instance at a temp
        # DB rather than patching its module-level bindings.
        self._orig_fa_path = file_access_singleton.path
        file_access_singleton.__init__(self.tmp / "file_access.db")

        self._patchers = [
            mock.patch(
                "pycodeloop.core.config._default_storage",
                lambda: SqliteSessions(path=self.tmp / "pycodeloop.db"),
            ),
            mock.patch(
                "pycodeloop.core.codeloop.JsonlTracer",
                lambda session_key: JsonlTracer(
                    session_key, directory=self.tmp / "logs"
                ),
            ),
            mock.patch(
                "pycodeloop.cli.commands.run.default_session_key",
                return_value="ci-session",
            ),
        ]
        for patcher in self._patchers:
            patcher.start()

        self.runner = CliRunner()

    def tearDown(self):
        for patcher in self._patchers:
            patcher.stop()
        file_access_singleton.__init__(self._orig_fa_path)
        console.file = sys.stdout
        os.chdir(self._cwd)
        self._tmpdir.cleanup()

    def _invoke(self, extra_args):
        server = FakeLLMServer(
            [
                chat_completion(
                    tool_calls=[
                        tool_call(
                            "c1",
                            "write_file",
                            {"path": "out.txt", "content": "hi"},
                        )
                    ]
                ),
                chat_completion(text="done"),
            ]
        )
        self.addCleanup(server.close)

        return self.runner.invoke(
            app,
            [
                "run",
                "do it",
                "--provider",
                "generic",
                "--url",
                server.url,
                "--model",
                "my-model",
                "-y",
                *extra_args,
            ],
        )

    def test_success_exit_zero_and_json_shape(self):
        result = self._invoke(["--ci", "--output", "json"])

        self.assertEqual(result.exit_code, 0, result.stdout + result.stderr)
        payload = __import__("json").loads(result.stdout)
        self.assertEqual(payload["status"], "success")
        self.assertGreaterEqual(payload["turns"], 1)
        self.assertIn("out.txt", payload["files_modified"])
        self.assertFalse(payload["regression"])

    def test_regression_exit_code_two(self):
        result = self._invoke(
            ["--ci", "--output", "json", "--check", "exit 1"]
        )

        self.assertEqual(result.exit_code, 2, result.stdout + result.stderr)
        payload = __import__("json").loads(result.stdout)
        self.assertTrue(payload["regression"])

    def test_budget_exit_code_three(self):
        result = self._invoke(
            ["--ci", "--output", "json", "--max-tokens", "1"]
        )

        self.assertEqual(result.exit_code, 3, result.stdout + result.stderr)
        payload = __import__("json").loads(result.stdout)
        self.assertEqual(payload["status"], "budget")

    def test_non_ci_keeps_zero_exit_on_regression(self):
        result = self._invoke(["--output", "json", "--check", "exit 1"])

        self.assertEqual(result.exit_code, 0, result.stdout + result.stderr)
        payload = __import__("json").loads(result.stdout)
        self.assertTrue(payload["regression"])


if __name__ == "__main__":
    unittest.main()
