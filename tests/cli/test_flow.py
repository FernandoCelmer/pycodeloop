"""Test flow.py's build_flow error paths and JSON-provider dispatch"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import typer

from pycodeloop.cli.flow import _load_mcp_tools, build_flow
from pycodeloop.core.mcp import MCPServer, MCPServerRegistry
from pycodeloop.core.persistence.local_config import JsonFileStore
from pycodeloop.core.persistence.sqlite_sessions import SqliteSessions
from pycodeloop.providers.generic import GenericProvider

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


class TestBuildFlowGenericProvider(unittest.TestCase):
    def test_generic_provider_without_url_exits(self):
        with self.assertRaises(typer.Exit):
            build_flow(provider_name="generic", model="m", url=None)

    def test_generic_provider_with_url_builds(self):
        flow, name, model = build_flow(
            provider_name="generic",
            model="my-model",
            url="http://fake/v1/chat/completions",
        )

        self.assertIsInstance(flow.agent.provider, GenericProvider)
        self.assertEqual(flow.agent.provider.url, "http://fake/v1/chat/completions")
        self.assertEqual(name, "generic")
        self.assertEqual(model, "my-model")


class TestBuildFlowJsonProvider(unittest.TestCase):
    def test_json_config_path_builds_generic_provider(self):
        flow, name, _model = build_flow(
            provider_name="templates/anthropic.json",
            model="explicit-model",
        )

        self.assertIsInstance(flow.agent.provider, GenericProvider)
        self.assertEqual(flow.agent.provider.model, "explicit-model")
        self.assertEqual(name, "templates/anthropic.json")


class TestBuildFlowCallbackWiring(unittest.TestCase):
    def test_agent_callbacks_are_all_wired(self):
        flow, _name, _model = build_flow(
            provider_name="generic",
            model="my-model",
            url="http://fake/v1/chat/completions",
        )

        self.assertIsNotNone(flow.agent.on_request)
        self.assertIsNotNone(flow.agent.on_tool_call)
        self.assertIsNotNone(flow.agent.on_tool_result)
        self.assertIsNotNone(flow.agent.on_text_delta)
        self.assertIsNotNone(flow.agent.on_usage)
        self.assertIsNotNone(flow.agent.confirm)

    def test_confirm_auto_approves_when_yes_flag_set(self):
        flow, _name, _model = build_flow(
            provider_name="generic",
            model="my-model",
            url="http://fake/v1/chat/completions",
            auto_approve=True,
        )

        self.assertTrue(flow.agent.confirm("bash", "$ echo hi"))

    def test_confirm_times_out_and_auto_confirms(self):
        flow, _name, _model = build_flow(
            provider_name="generic",
            model="my-model",
            url="http://fake/v1/chat/completions",
        )

        with mock.patch("pycodeloop.cli.flow._CONFIRM_TIMEOUT", 0.05):
            # No stdin input is available in a test process, so the
            # background reader thread just blocks on input() forever
            # and this must time out and auto-confirm rather than hang.
            result = flow.agent.confirm("bash", "$ echo hi")

        self.assertTrue(result)


class TestLoadMcpToolsSavedServers(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

        store = JsonFileStore(Path(self._tmpdir.name) / "config.json")
        patcher = mock.patch("pycodeloop.core.mcp.default_store", store)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_resolves_saved_server_by_name(self):
        MCPServerRegistry().save(
            "fs", MCPServer(command="npx", args=["-y", "fs-server"])
        )

        with mock.patch(
            "pycodeloop.cli.flow.load_mcp_tools", return_value=[]
        ) as load_tools:
            _load_mcp_tools(["saved:fs"])

        called_server = load_tools.call_args[0][0]
        self.assertEqual(called_server.command, "npx")
        self.assertEqual(called_server.args, ["-y", "fs-server"])

    def test_unknown_saved_server_exits(self):
        with self.assertRaises(typer.Exit):
            _load_mcp_tools(["saved:nope"])


if __name__ == "__main__":
    unittest.main()
