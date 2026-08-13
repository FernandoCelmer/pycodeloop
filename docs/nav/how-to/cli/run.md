# pycodeloop run

Run a single prompt to completion, non-interactively.

```bash
pycodeloop run "add a docstring to pycodeloop/core/agent.py"
```

## Options

| Option | Description |
|--------|-------------|
| `--provider` | `path/to/config.json` (see `templates/`) \| `generic` (with `--url`) \| `module.path:ClassName` for a custom [`Provider`](../../reference/abc-provider.md) |
| `--model` | Model name override |
| `--base-url` | Override the API endpoint (local/self-hosted servers) — only applies with `--provider generic` |
| `--url` | Endpoint URL, required when `--provider generic` |
| `--mcp` | MCP server as `"command arg1 arg2"`; repeatable |
| `--skills` / `--no-skills` | Discover Claude/Cursor/AGENTS.md skills and expose a `read_skill` tool. On by default — see [Skills](../skills.md) |
| `--skills-refresh` | Bypass the skills cache and rescan |
| `--yes` / `-y` | Skip confirmation prompts for dangerous tools |

There's no bare `anthropic`/`openai`/`ollama` provider name — every vendor is a `GenericProvider` pointed at a JSON config (see [`templates/`](https://github.com/dotflow-io/pycodeloop/tree/master/templates)) or, for an ad-hoc OpenAI-compatible endpoint, `--provider generic --url ...`.

## Examples

```bash
# Anthropic, via the bundled template (also the default with no --provider)
pycodeloop run "..." --provider templates/anthropic.json

# OpenAI, with a model override
pycodeloop run "..." --provider templates/openai.json --model gpt-5

# Local model via Ollama
pycodeloop run "..." --provider templates/ollama.json --model llama3.1

# JSON-configured provider, no Python required
pycodeloop run "..." --provider ./provider.example.json

# With an MCP server, no confirmation prompts
pycodeloop run "..." --mcp "npx -y @modelcontextprotocol/server-filesystem ." --yes
```

See also: [`pycodeloop chat`](chat.md) for the full-screen interactive interface (the default with no subcommand).
