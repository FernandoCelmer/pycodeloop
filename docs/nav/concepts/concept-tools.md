# Tools

`Tool` (`pycodeloop.abc.tool.Tool`) is the interface for any action the agent can take:

```python
class Tool(ABC):
    name: str
    description: str
    parameters: dict            # JSON schema
    dangerous: bool = False
    concurrent_safe: bool = False

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
| `http_request` | Call a JSON HTTP API — any method, headers, body | Yes |
| `git_status` | `git status --porcelain=v1 --branch` | No |
| `git_diff` | Unstaged (or staged) changes as a unified diff | No |
| `git_log` | Recent commit history, one line per commit | No |
| `git_commit` | Stage files and create a commit | Yes |
| `env` | Read environment variables (sensitive values masked) | No |
| `sql_schema` | List a database's tables, or one table's columns | No |
| `sql_query` | Run a single read-only SQL statement (SELECT/WITH/EXPLAIN/PRAGMA/SHOW/DESCRIBE) | No |
| `delegate` | Spawn a fresh sub-agent (same provider, read-only tools) for an independent subtask — `Config(delegation=True)` / `--delegate`, off by default | No |
| `remember` | Save a standing correction/preference to `.pycodeloop/memory.md` — `Config(memory=True)` / `--memory`, on by default | No |

`DEFAULT_TOOLS` (`pycodeloop.tools.DEFAULT_TOOLS`) is that list (everything above except `delegate`/`remember`, which `Config` appends conditionally), ready to pass into `Config`. `READ_ONLY_TOOLS` (`pycodeloop.tools.READ_ONLY_TOOLS`) is the read-only subset — `read_file`/`list_dir`/`glob`/`grep`/`web_fetch`/`git_status`/`git_diff`/`git_log`/`sql_schema`/`sql_query` — that `delegate` hands to each sub-agent.

## Token-saving read cache

`read_file` logs every read/write/edit/delete to a `file_access` table in `~/.pycodeloop/pycodeloop.db`, scoped to the active session (`session_key`, or `"global"` outside one). If the exact same `path`/`offset`/`limit` is read again in the same session and the file hasn't changed since (content hash matches), it returns a short "unchanged since you last read" notice instead of repeating the content — pass `force=true` to see the full content again (e.g. after compaction dropped it from context).

## Running the same tool multiple times in one turn

By default, if a model calls the same tool name more than once in a single turn, `Agent` runs those calls sequentially — safe for tools with any shared mutable state. Set `concurrent_safe = True` on a `Tool` subclass to opt its repeated calls into running in parallel instead (calls to *different*-named tools already run concurrently regardless of this flag, as long as none of them is `dangerous`). `delegate` sets this, which is what lets several sub-agents fan out and run at the same time.

## Dangerous tools and preview

A tool marked `dangerous = True` gets a confirmation gate: before `Agent` runs it, it calls `tool.preview(**arguments)` and passes the result to the `confirm` hook. If `confirm` returns `False`, the tool never runs and the model is told "User declined to run this tool."

`preview()` defaults to a repr of the arguments, but the built-in dangerous tools override it:

- `write_file` / `edit_file` / `delete_file` — a unified diff of what would change
- `bash` — the literal command line (`$ ...`)
- MCP tools — the call rendered as `tool_name(arg=value, ...)`

See [Permission prompts](../how-to/permission-prompts.md) for how the CLI renders this.

## MCP tools

Tools don't have to be local Python code. `pycodeloop.mcp.load_mcp_tools(server)` connects to a [Model Context Protocol](https://modelcontextprotocol.io/) server and returns its remote tools already wrapped as `Tool` instances — the agent can't tell an MCP tool from a local one. See [MCP servers](../how-to/mcp-servers.md).

## Skills

When skills discovery is on, `Config` appends a `read_skill` tool and lists every discovered skill in the system prompt, so the agent can pull one in on demand. See [Skills](../how-to/skills.md).

## Writing your own

See [Custom tools](../how-to/custom-tool.md).
