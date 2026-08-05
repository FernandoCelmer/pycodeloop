# Install

```bash
pip install aiflow[anthropic]   # Claude
pip install aiflow[openai]      # GPT / any OpenAI-compatible server, incl. Ollama
pip install aiflow[mcp]         # MCP server integration
pip install aiflow[all]         # everything
```

Or with Poetry, inside a clone of the repo:

```bash
poetry install --extras all
```

## Configure

```bash
export AIFLOW_PROVIDER=anthropic   # or: openai, ollama
export AIFLOW_MODEL=claude-sonnet-5
export ANTHROPIC_API_KEY=sk-...    # or OPENAI_API_KEY
```

These are only defaults — every entrypoint (`Config(provider=...)`, `aiflow run --provider ...`) lets you override them explicitly.
