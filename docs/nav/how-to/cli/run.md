# aiflow run

Run a single prompt to completion, non-interactively.

```bash
aiflow run "add a docstring to aiflow/core/agent.py"
```

## Options

| Option | Description |
|--------|-------------|
| `--provider` | `anthropic` \| `openai` \| `ollama` \| `module.path:ClassName` for a custom [`Provider`](../../reference/abc-provider.md) |
| `--model` | Model name override |
| `--base-url` | Override the API endpoint — any OpenAI-compatible local/self-hosted server |
| `--mcp` | MCP server as `"command arg1 arg2"`; repeatable |
| `--yes` / `-y` | Skip confirmation prompts for dangerous tools |

## Examples

```bash
# Different provider and model
aiflow run "..." --provider openai --model gpt-5

# Local model via Ollama
aiflow run "..." --provider ollama --model llama3.1

# With an MCP server, no confirmation prompts
aiflow run "..." --mcp "npx -y @modelcontextprotocol/server-filesystem ." --yes
```
