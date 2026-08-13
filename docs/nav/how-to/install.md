# Install

```bash
pip install pycodeloop
```

`GenericProvider` talks to Anthropic, OpenAI, Ollama, and any other HTTP chat-completions-style API via the stdlib/`httpx` — no vendor SDK required, so the plain install covers every provider. The only optional extra is `mcp`, needed if you connect to [Model Context Protocol](https://modelcontextprotocol.io/) servers:

```bash
pip install pycodeloop[mcp]         # MCP server integration
```

Or with Poetry, inside a clone of the repo:

```bash
poetry install --extras mcp
```

## Configure

The bundled default is Anthropic (`templates/anthropic.json`, resolved automatically) — set `ANTHROPIC_API_KEY` and you're done. To point at a different backend, override `PYCODELOOP_PROVIDER` with a path to another JSON config (see [`templates/`](https://github.com/dotflow-io/pycodeloop/tree/master/templates)) or `generic` paired with `--url`:

```bash
export ANTHROPIC_API_KEY=sk-...

# or a different backend:
export PYCODELOOP_PROVIDER=templates/openai.json
export PYCODELOOP_MODEL=gpt-5
export OPENAI_API_KEY=sk-...
```

These are only defaults — every entrypoint (`Config(provider=...)`, `pycodeloop run --provider ...`) lets you override them explicitly.

## VS Code extension

The `vscode-extension/` folder in the repo has a CodeLoop sidebar chat for VS Code — see its [README](https://github.com/dotflow-io/pycodeloop/blob/master/vscode-extension/README.md) for features and setup. It talks to `pycodeloop serve` over JSON-RPC instead of the terminal CLI.
