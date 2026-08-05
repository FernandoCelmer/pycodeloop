from aiflow.core.mcp import MCPTool


class FakeMCPClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def call_tool(self, name: str, arguments: dict) -> str:
        self.calls.append((name, arguments))
        if name == "boom":
            raise RuntimeError("remote failure")
        return f"{name} result"


def test_mcp_tool_schema_from_server():
    client = FakeMCPClient()
    schema = {
        "name": "search_docs",
        "description": "Search the docs.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
    }

    tool = MCPTool(client, schema)

    assert tool.name == "search_docs"
    assert tool.description == "Search the docs."
    assert tool.schema()["parameters"] == schema["input_schema"]


def test_mcp_tool_run_delegates_to_client():
    client = FakeMCPClient()
    tool = MCPTool(client, {"name": "search_docs", "description": "", "input_schema": {}})

    result = tool.run(query="hello")

    assert result.output == "search_docs result"
    assert not result.is_error
    assert client.calls == [("search_docs", {"query": "hello"})]


def test_mcp_tool_run_reports_remote_error():
    client = FakeMCPClient()
    tool = MCPTool(client, {"name": "boom", "description": "", "input_schema": {}})

    result = tool.run()

    assert result.is_error
    assert "remote failure" in result.output
