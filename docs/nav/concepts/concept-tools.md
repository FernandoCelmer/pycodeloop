# Tools

`Tool` (`aiflow.abc.tool.Tool`) is the interface for any action the agent can take:

```python
class Tool(ABC):
    name: str
    description: str
    parameters: dict            # JSON schema
    dangerous: bool = False

    def schema(self) -> dict: ...
    def preview(self, **kwargs) -> str: ...
    def run(self, **kwargs) -> ToolResult: ...
```

## Built-in tools

| Tool | Purpose | `dangerous` |
|------|---------|--------------|
| `read_file` | Read a file, optionally a line range | No |
| `write_file` | Create or overwrite a file | Yes |
| `edit_file` | Replace an exact substring in a file | Yes |
| `delete_file` | Delete a file | Yes |
| `list_dir` | List a directory | No |
| `glob` | Find files matching a glob pattern | No |
| `grep` | Regex search across files | No |
| `bash` | Run a shell command with a timeout | Yes |
| `web_fetch` | Fetch a URL and extract its text | No |

`DEFAULT_TOOLS` (`aiflow.core.tools.DEFAULT_TOOLS`) is that list, ready to pass into `Config`.

## Dangerous tools and preview

A tool marked `dangerous = True` gets a confirmation gate: before `Agent` runs it, it calls `tool.preview(**arguments)` and passes the result to the `confirm` hook. If `confirm` returns `False`, the tool never runs and the model is told "User declined to run this tool."

`preview()` defaults to a repr of the arguments, but the built-in dangerous tools override it:

- `write_file` / `edit_file` / `delete_file` — a unified diff of what would change
- `bash` — the literal command line (`$ ...`)
- MCP tools — the call rendered as `tool_name(arg=value, ...)`

See [Permission prompts](../how-to/permission-prompts.md) for how the CLI renders this.

## MCP tools

Tools don't have to be local Python code. `aiflow.core.mcp.load_mcp_tools(server)` connects to a [Model Context Protocol](https://modelcontextprotocol.io/) server and returns its remote tools already wrapped as `Tool` instances — the agent can't tell an MCP tool from a local one. See [MCP servers](../how-to/mcp-servers.md).

## Skills

When skills discovery is on, `Config` appends a `read_skill` tool and lists every discovered skill in the system prompt, so the agent can pull one in on demand. See [Skills](../how-to/skills.md).

## Writing your own

See [Custom tools](../how-to/custom-tool.md).
