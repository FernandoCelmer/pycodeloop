# Install

```bash
pip install pycodeloop[anthropic]   # Claude
pip install pycodeloop[openai]      # GPT / any OpenAI-compatible server, incl. Ollama
pip install pycodeloop[mcp]         # MCP server integration
pip install pycodeloop[all]         # everything
```

Or with Poetry, inside a clone of the repo:

```bash
poetry install --extras all
```

## Configure

```bash
export PYCODELOOP_PROVIDER=anthropic   # or: openai, ollama
export PYCODELOOP_MODEL=claude-sonnet-5
export ANTHROPIC_API_KEY=sk-...    # or OPENAI_API_KEY
```

These are only defaults — every entrypoint (`Config(provider=...)`, `pycodeloop run --provider ...`) lets you override them explicitly.
