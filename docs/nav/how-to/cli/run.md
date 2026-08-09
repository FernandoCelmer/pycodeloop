# codeloop run

Run a single prompt to completion, non-interactively.

```bash
codeloop run "add a docstring to codeloop/core/agent.py"
```

## Options

| Option | Description |
|--------|-------------|
| `--provider` | `anthropic` \| `openai` \| `ollama` \| `generic` \| `path/to/config.json` \| `module.path:ClassName` for a custom [`Provider`](../../reference/abc-provider.md) |
| `--model` | Model name override |
| `--base-url` | Override the API endpoint — any OpenAI-compatible local/self-hosted server |
| `--url` | Endpoint URL, required when `--provider generic` |
| `--mcp` | MCP server as `"command arg1 arg2"`; repeatable |
| `--skills` / `--no-skills` | Discover Claude/Cursor/AGENTS.md skills and expose a `read_skill` tool. On by default — see [Skills](../skills.md) |
| `--skills-refresh` | Bypass the skills cache and rescan |
| `--yes` / `-y` | Skip confirmation prompts for dangerous tools |

## Examples

```bash
# Different provider and model
codeloop run "..." --provider openai --model gpt-5

# Local model via Ollama
codeloop run "..." --provider ollama --model llama3.1

# JSON-configured provider, no Python required
codeloop run "..." --provider ./provider.example.json

# With an MCP server, no confirmation prompts
codeloop run "..." --mcp "npx -y @modelcontextprotocol/server-filesystem ." --yes
```

See also: [`codeloop tui`](tui.md) for the full-screen interactive interface (the default with no subcommand).
