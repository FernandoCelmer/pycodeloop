"""Test MCPTool class"""

import unittest

from aiflow.core.mcp import MCPTool


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


if __name__ == "__main__":
    unittest.main()
