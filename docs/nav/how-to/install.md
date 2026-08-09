# Install

```bash
pip install codeloop[anthropic]   # Claude
pip install codeloop[openai]      # GPT / any OpenAI-compatible server, incl. Ollama
pip install codeloop[mcp]         # MCP server integration
pip install codeloop[all]         # everything
```

Or with Poetry, inside a clone of the repo:

```bash
poetry install --extras all
```

## Configure

```bash
export CODELOOP_PROVIDER=anthropic   # or: openai, ollama
export CODELOOP_MODEL=claude-sonnet-5
export ANTHROPIC_API_KEY=sk-...    # or OPENAI_API_KEY
```

These are only defaults — every entrypoint (`Config(provider=...)`, `codeloop run --provider ...`) lets you override them explicitly.
