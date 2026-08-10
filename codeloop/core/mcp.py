"""MCP module"""

from __future__ import annotations

import asyncio
import atexit
import threading
from contextlib import AsyncExitStack
from dataclasses import dataclass, field

from codeloop.abc.settings import Settings
from codeloop.abc.tool import Tool, ToolResult
from codeloop.core.persistence.local_config import default_store

_MCP_SECTION = "mcp_servers"


@dataclass
class MCPServer:
    """
    Import:
        You can import the **MCPServer** class with:

            from codeloop.core.mcp import MCPServer, load_mcp_tools

    Example:
        `class` codeloop.core.mcp.MCPServer

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
    """Adapts one remote MCP tool into the codeloop Tool ABC."""

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
    """Connect to an MCP server, return its tools as codeloop Tools.

    The client's subprocess/thread are registered for cleanup at
    interpreter exit — nothing else in the app ever called `close()`,
    which otherwise leaked a live MCP server subprocess per connection."""
    client = MCPClient(server)
    atexit.register(client.close)

    return [MCPTool(client, schema) for schema in client.list_tools()]


class MCPServerRegistry:
    """Named `MCPServer` configs saved in `~/.codeloop/config.json`
    under "mcp_servers", so the CLI can reference one later as
    `--mcp saved:<name>` instead of repeating the full command."""

    def __init__(self, store: Settings | None = None) -> None:
        self.store = store or default_store

    def save(self, name: str, server: MCPServer) -> None:
        servers = self.store.get_section(_MCP_SECTION)
        servers[name] = {
            "command": server.command,
            "args": server.args,
            "env": server.env,
        }

        self.store.set_section(_MCP_SECTION, servers)

    def load(self, name: str) -> MCPServer | None:
        data = self.store.get_section(_MCP_SECTION).get(name)

        if data is None:
            return None

        return MCPServer(
            command=data["command"], args=data.get("args", []), env=data.get("env")
        )

    def list(self) -> dict:
        return self.store.get_section(_MCP_SECTION)

    def delete(self, name: str) -> None:
        servers = self.store.get_section(_MCP_SECTION)
        servers.pop(name, None)

        self.store.set_section(_MCP_SECTION, servers)
