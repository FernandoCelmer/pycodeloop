"""Test MCPTool class"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from codeloop.core import local_config
from codeloop.core.mcp import (
    MCPServer,
    MCPTool,
    delete_mcp_server,
    list_mcp_servers,
    load_mcp_server,
    save_mcp_server,
)


class FakeMCPClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def call_tool(self, name: str, arguments: dict) -> str:
        self.calls.append((name, arguments))
        if name == "boom":
            raise RuntimeError("remote failure")
        return f"{name} result"


class TestMCPTool(unittest.TestCase):
    def test_schema_from_server(self):
        client = FakeMCPClient()
        schema = {
            "name": "search_docs",
            "description": "Search the docs.",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        }

        tool = MCPTool(client, schema)

        self.assertEqual(tool.name, "search_docs")
        self.assertEqual(tool.description, "Search the docs.")
        self.assertEqual(tool.schema()["parameters"], schema["input_schema"])

    def test_run_delegates_to_client(self):
        client = FakeMCPClient()
        tool = MCPTool(
            client,
            {"name": "search_docs", "description": "", "input_schema": {}},
        )

        result = tool.run(query="hello")

        self.assertEqual(result.output, "search_docs result")
        self.assertFalse(result.is_error)
        self.assertEqual(client.calls, [("search_docs", {"query": "hello"})])

    def test_run_reports_remote_error(self):
        client = FakeMCPClient()
        tool = MCPTool(client, {"name": "boom", "description": "", "input_schema": {}})

        result = tool.run()

        self.assertTrue(result.is_error)
        self.assertIn("remote failure", result.output)


class TestSavedMCPServers(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

        patcher = mock.patch.object(
            local_config, "CONFIG_PATH", Path(self._tmpdir.name) / "config.json"
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_save_then_load_roundtrips(self):
        server = MCPServer(command="npx", args=["-y", "server-filesystem", "."])

        save_mcp_server("fs", server)
        loaded = load_mcp_server("fs")

        self.assertEqual(loaded, server)

    def test_load_missing_name_returns_none(self):
        self.assertIsNone(load_mcp_server("nope"))

    def test_list_mcp_servers_returns_all_saved(self):
        save_mcp_server("fs", MCPServer(command="npx", args=["fs"]))
        save_mcp_server("db", MCPServer(command="npx", args=["db"]))

        names = set(list_mcp_servers())

        self.assertEqual(names, {"fs", "db"})

    def test_delete_mcp_server_removes_it(self):
        save_mcp_server("fs", MCPServer(command="npx", args=["fs"]))

        delete_mcp_server("fs")

        self.assertIsNone(load_mcp_server("fs"))


if __name__ == "__main__":
    unittest.main()
