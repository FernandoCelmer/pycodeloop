"""Functional: `build_flow()` wired exactly as the CLI wires it, driven
against a real HTTP socket, running a real tool-use turn end to end."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pycodeloop.cli.flow import build_flow
from pycodeloop.core.store.sqlite_sessions import SqliteSessions
from tests.functional._fake_llm_server import (
    FakeLLMServer,
    chat_completion,
    tool_call,
)

# build_flow() -> Config() defaults storage to a real SqliteSessions() at
# ~/.pycodeloop/pycodeloop.db when not given one explicitly — every test
# in this module would otherwise write to the real user's database.
_tmpdir = tempfile.TemporaryDirectory()
_default_storage_patcher = mock.patch(
    "pycodeloop.core.config._default_storage",
    lambda: SqliteSessions(path=Path(_tmpdir.name) / "pycodeloop.db"),
)


def setUpModule():
    _default_storage_patcher.start()


def tearDownModule():
    _default_storage_patcher.stop()
    _tmpdir.cleanup()


class TestBuildFlowEndToEnd(unittest.TestCase):
    def test_full_turn_over_real_socket_with_auto_approve(self):
        server = FakeLLMServer(
            [
                chat_completion(
                    tool_calls=[tool_call("call-1", "list_dir", {"path": "."})]
                ),
                chat_completion(text="Here's what's in the directory."),
            ]
        )
        self.addCleanup(server.close)

        flow, name, model = build_flow(
            provider_name="generic",
            model="my-model",
            url=server.url,
            auto_approve=True,
        )

        self.assertEqual(name, "generic")
        self.assertEqual(model, "my-model")

        result = flow.run("list the current directory")

        self.assertEqual(result, "Here's what's in the directory.")
        self.assertEqual(len(server.requests), 2)
        first_request_tools = {
            t["function"]["name"] for t in server.requests[0]["tools"]
        }
        self.assertIn("list_dir", first_request_tools)


if __name__ == "__main__":
    unittest.main()
