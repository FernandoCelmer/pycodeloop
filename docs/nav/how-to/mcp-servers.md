# MCP servers

```bash
pip install pypycodeloop[mcp]
```

Connect to any [Model Context Protocol](https://modelcontextprotocol.io/) server over stdio and expose its tools to the agent alongside the built-in ones.

## As a library

```python
from pycodeloop import CodeLoop, Config
from pycodeloop.core.mcp import MCPServer, load_mcp_tools
from pycodeloop.core.tools import DEFAULT_TOOLS
from pycodeloop.providers import AnthropicProvider

server = MCPServer(command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", "."])
tools = DEFAULT_TOOLS + load_mcp_tools(server)

config = Config(provider=AnthropicProvider(model="claude-sonnet-5"), tools=tools)
flow = CodeLoop(config=config)
```

`load_mcp_tools(server)` connects, lists the server's tools, and returns each one wrapped as a regular `Tool` — `Agent` doesn't know or care that the call is going over stdio to a subprocess instead of running in-process.

## From the CLI

One `--mcp` flag per server, `command arg1 arg2` shell-quoted:

```bash
pycodeloop run "list every allowed directory" \
  --mcp "npx -y @modelcontextprotocol/server-filesystem ."
```

## Lifecycle

`MCPClient` (`pycodeloop.core.mcp.MCPClient`) owns the server subprocess on a dedicated background event loop for the life of the process — MCP sessions are async and expect to live inside one `async with` block for their whole lifetime, so a background loop lets a synchronous `Tool.run()` call into a long-lived subprocess without blocking `Agent`.

Every MCP tool is `dangerous = True` by default (see [Permission prompts](permission-prompts.md)) since a remote server's tools are opaque — its `preview()` renders the call as `tool_name(arg=value, ...)`.
