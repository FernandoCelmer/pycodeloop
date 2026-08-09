"""MCP module"""

from __future__ import annotations

import asyncio
import threading
from contextlib import AsyncExitStack
from dataclasses import dataclass, field

from aiflow.abc.tool import Tool, ToolResult


@dataclass
class MCPServer:
    """
    Import:
        You can import the **MCPServer** class with:

            from aiflow.core.mcp import MCPServer, load_mcp_tools

    Example:
        `class` aiflow.core.mcp.MCPServer

            server = MCPServer(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "."],
            )
            tools = load_mcp_tools(server)

            config = Config(tools=DEFAULT_TOOLS + tools)

    Args:
        command (str): Executable that speaks MCP over stdio.
        args (Optional[List[str]]): Arguments passed to the command.
        env (Optional[Dict[str, str]]): Extra environment variables.
    """

    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None


class MCPClient:
    """One MCP server subprocess on a dedicated background event loop —
    bridges its async session into synchronous `Tool.run()` calls."""

    def __init__(self, server: MCPServer) -> None:
        self.server = server
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._exit_stack = None
        self._session = None
        self._run(self._connect())

    def _run(self, coro, timeout: float = 30):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    async def _connect(self) -> None:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        self._exit_stack = AsyncExitStack()
        params = StdioServerParameters(
            command=self.server.command,
            args=self.server.args,
            env=self.server.env,
        )
        read, write = await self._exit_stack.enter_async_context(stdio_client(params))
        session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._session = session

    def list_tools(self) -> list[dict]:
        return self._run(self._list_tools())

    async def _list_tools(self) -> list[dict]:
        result = await self._session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": (
                    getattr(tool, "input_schema", None)
                    or getattr(tool, "inputSchema", None)
                    or {"type": "object", "properties": {}}
                ),
            }
            for tool in result.tools
        ]

    def call_tool(self, name: str, arguments: dict) -> str:
        return self._run(self._call_tool(name, arguments), timeout=120)

    async def _call_tool(self, name: str, arguments: dict) -> str:
        result = await self._session.call_tool(name, arguments)
        parts = [block.text for block in result.content if getattr(block, "text", None)]
        return "\n".join(parts) if parts else str(result.content)

    def close(self) -> None:
        if self._exit_stack is not None:
            self._run(self._exit_stack.aclose())
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)


class MCPTool(Tool):
    """Adapts one remote MCP tool into the aiflow Tool ABC."""

    dangerous = True

    def __init__(self, client: MCPClient, schema: dict) -> None:
        self.client = client
        self.name = schema["name"]
        self.description = schema["description"]
        self.parameters = schema["input_schema"]

    def preview(self, **kwargs) -> str:
        args = ", ".join(f"{key}={value!r}" for key, value in kwargs.items())
        return f"{self.name}({args})"

    def run(self, **kwargs) -> ToolResult:
        try:
            output = self.client.call_tool(self.name, kwargs)
        except Exception as exc:
            return ToolResult(
                output=f"Error calling MCP tool '{self.name}': {exc}",
                is_error=True,
            )
        return ToolResult(output=output)


def load_mcp_tools(server: MCPServer) -> list[Tool]:
    """Connect to an MCP server, return its tools as aiflow Tools."""
    client = MCPClient(server)
    return [MCPTool(client, schema) for schema in client.list_tools()]
