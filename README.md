<div align="center">

**Bring your own model. Swap providers. Ship an agent.**

[![PyPI](https://img.shields.io/pypi/v/aiflow?style=flat-square)](https://pypi.org/project/aiflow/)
[![Python](https://img.shields.io/pypi/pyversions/aiflow?style=flat-square)](https://pypi.org/project/aiflow/)
[![Stars](https://img.shields.io/github/stars/dotflow-io?label=Stars&style=flat-square)](https://github.com/dotflow-io/aiflow)

[Repository](https://github.com/dotflow-io/aiflow)

</div>

---

# AIFlow

AIFlow is a lightweight Python library for building agentic coding assistants — in the shape of Claude Code, Codex, or Gemini CLI. Give it a provider and a prompt, it drives a tool-use loop (read, write, edit, grep, bash, web fetch) until the task is done. Same shape everywhere: swap Anthropic for OpenAI without touching the agent loop.

## Why AIFlow?

- **Simple** — `AIFlow(config=Config(...)).run("do the thing")`. That's it.
- **Multi-provider** — Anthropic, OpenAI, Ollama, any OpenAI-compatible server, or a JSON-configured/custom backend.
- **Decoupled** — providers, tools, and the system prompt are injected, not hardcoded.
- **Embeddable** — use it as a library inside your own app, or drive it from the `aiflow` CLI.
- **Extensible tools** — read/write/edit/delete/list/glob/grep/bash/web-fetch out of the box; add your own by subclassing `Tool`.
- **Full-screen TUI** — bare `aiflow` drops you into a Textual-based interface; `run`/`chat` stay available for scripting.
- **Skills-aware** — auto-discovers Claude Code, Cursor, and `AGENTS.md` skills already on disk and exposes them to the agent.

## Install

```bash
pip install aiflow[anthropic]   # or: aiflow[openai], aiflow[all]
```

## Quick Start

```python
from aiflow import AIFlow, Config
from aiflow.providers import AnthropicProvider

config = Config(
    provider=AnthropicProvider(model="claude-sonnet-5"),
)

flow = AIFlow(config=config)
print(flow.run("list the files in this repo and summarize the project"))
```

## Optional extras

```bash
pip install aiflow[anthropic]   # Claude
pip install aiflow[openai]      # GPT
pip install aiflow[all]         # both
```

## Features

<details>
<summary><strong>Providers</strong></summary>

Swap the LLM backend without touching the agent loop:

```python
from aiflow import Config
from aiflow.providers import AnthropicProvider, OpenAIProvider

# Anthropic
config = Config(provider=AnthropicProvider(model="claude-sonnet-5"))

# OpenAI
config = Config(provider=OpenAIProvider(model="gpt-5"))
```

Env-based defaults, resolved by `aiflow.settings.Settings` when `Config()` gets no explicit provider:

```bash
export AIFLOW_PROVIDER=anthropic   # or: openai
export AIFLOW_MODEL=claude-sonnet-5
export ANTHROPIC_API_KEY=sk-...    # or OPENAI_API_KEY
```

Point `GenericProvider` at any OpenAI-compatible HTTP endpoint, or configure one entirely from a JSON file — no Python required:

```python
from aiflow.providers import get_provider

provider = get_provider("./provider.example.json")
```

```bash
aiflow run "list the files here" --provider ./provider.example.json
```

See [`docs/examples/provider.example.json`](docs/examples/provider.example.json) and the [JSON provider guide](docs/nav/development/json-provider.md).

Bring your own backend by implementing the `Provider` ABC:

```python
from aiflow.abc.provider import Provider, ProviderResponse

class MyProvider(Provider):
    def complete(self, system_prompt, messages, tools) -> ProviderResponse:
        ...
```

---

</details>

<details>
<summary><strong>Dependency Injection via Config</strong></summary>

The `Config` class validates and injects the pieces an agent run needs:

```python
from aiflow import Config
from aiflow.providers import AnthropicProvider
from aiflow.core.tools import DEFAULT_TOOLS

config = Config(
    provider=AnthropicProvider(model="claude-sonnet-5"),
    tools=DEFAULT_TOOLS,
    system_prompt="You are a terse code reviewer.",
    max_turns=25,
)
```

Passing anything that isn't a `Provider` instance raises `NotProviderInstance` at construction time, not mid-run.

---

</details>

<details>
<summary><strong>Tools</strong></summary>

Ships with the actions an agent needs to actually change code:

| Tool | Purpose |
|------|---------|
| `read_file` | Read a file, optionally a line range |
| `write_file` | Create or overwrite a file |
| `edit_file` | Replace an exact substring in a file |
| `delete_file` | Delete a file |
| `list_dir` | List a directory |
| `glob` | Find files matching a glob pattern |
| `grep` | Regex search across files |
| `bash` | Run a shell command with a timeout |
| `web_fetch` | Fetch a URL and extract its text |

Add your own by subclassing `Tool`:

```python
from aiflow.abc.tool import Tool, ToolResult

class MyTool(Tool):
    name = "my_tool"
    description = "Does a thing."
    parameters = {"type": "object", "properties": {"x": {"type": "string"}}}

    def run(self, x: str) -> ToolResult:
        return ToolResult(output=f"did {x}")
```

Mark a tool `dangerous = True` and it gets a confirmation gate before it runs — `write_file`, `edit_file`, `delete_file`, `bash`, and every MCP tool already are. Override `preview(**kwargs)` to control what's shown at confirmation time (defaults to a diff for file tools, the command line for `bash`):

```python
from aiflow.core.agent import Agent

def confirm(name: str, preview: str) -> bool:
    print(preview)
    return input(f"run {name}? [y/N] ").lower() == "y"

agent = Agent(provider=provider, confirm=confirm)
```

---

</details>

<details>
<summary><strong>Streaming and token usage</strong></summary>

`Agent` exposes hooks for everything the terminal UI needs — streamed text, per-turn and cumulative token usage:

```python
from aiflow.core.agent import Agent

agent = Agent(
    provider=provider,
    on_text_delta=lambda chunk: print(chunk, end=""),
    on_usage=lambda turn, total: print(f"\n{turn.input_tokens}in/{turn.output_tokens}out, total {total.input_tokens}in/{total.output_tokens}out"),
)

agent.run("...")
print(agent.usage)  # Usage(input_tokens=..., output_tokens=...)
```

`on_text_delta` only fires when the provider supports streaming (Anthropic and OpenAI both do); leave it `None` to get the assembled response in one shot instead.

---

</details>

<details>
<summary><strong>MCP servers</strong></summary>

```bash
pip install aiflow[mcp]
```

Connect to any Model Context Protocol server over stdio and expose its remote tools to the agent alongside the built-in ones:

```python
from aiflow import AIFlow, Config
from aiflow.core.mcp import MCPServer, load_mcp_tools
from aiflow.core.tools import DEFAULT_TOOLS
from aiflow.providers import AnthropicProvider

server = MCPServer(command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", "."])
tools = DEFAULT_TOOLS + load_mcp_tools(server)

config = Config(provider=AnthropicProvider(model="claude-sonnet-5"), tools=tools)
flow = AIFlow(config=config)
```

Or from the CLI, one `--mcp` flag per server:

```bash
aiflow run "list every allowed directory" \
  --mcp "npx -y @modelcontextprotocol/server-filesystem ."
```

`load_mcp_tools` keeps the server subprocess alive on a background event loop for the life of the process, and adapts each remote tool schema into a regular `Tool` — the agent can't tell an MCP tool from a local one.

---

</details>

<details>
<summary><strong>CLI</strong></summary>

Run the agent directly from the command line:

```bash
# Bare aiflow drops into the full-screen Textual TUI
aiflow

# One-shot
aiflow run "add a docstring to aiflow/core/agent.py"

# Interactive plain-terminal session, conversation history kept across turns
aiflow chat

# Override provider/model per invocation
aiflow run "..." --provider openai --model gpt-5

# Skip confirmation prompts for dangerous tools
aiflow run "..." --yes

# Skip skills auto-discovery
aiflow run "..." --no-skills
```

The CLI behaves like a terminal coding agent:

- **Streams** the model's text as it arrives instead of waiting for the full reply.
- **Asks before running** `write_file`, `edit_file`, `delete_file`, `bash`, or any MCP tool — shows a colored diff (or the shell command) and waits for confirmation. `--yes` skips this.
- **Reports token usage** after every turn: input/output tokens for that turn plus the running session total.
- **Discovers skills automatically** — `SKILL.md`/`CLAUDE.md` (Claude Code), `.mdc`/`.cursorrules` (Cursor), and `AGENTS.md` files already on disk are indexed and exposed to the agent via a `read_skill` tool, cached in `~/.aiflow/config.json` until something changes. `--no-skills` turns this off; `--skills-refresh` bypasses the cache.

---

</details>

<details>
<summary><strong>Low-level Agent loop</strong></summary>

`AIFlow` is a thin wrapper around `Agent` + `Session` for when you want direct control over the tool-use loop, hooks, or multi-turn state:

```python
from aiflow.core.agent import Agent
from aiflow.providers import AnthropicProvider

def on_tool_call(name, args):
    print(f"-> {name} {args}")

agent = Agent(
    provider=AnthropicProvider(model="claude-sonnet-5"),
    on_tool_call=on_tool_call,
)

reply = agent.run("fix the failing test in tests/test_agent.py")
```

---

</details>

## Commit Style

| Icon | Type      | Description                                |
|------|-----------|--------------------------------------------|
| ⚙️   | FEATURE   | New feature                                |
| 📝   | PEP8      | Formatting fixes following PEP8            |
| 📌   | ISSUE     | Reference to issue                         |
| 🪲   | BUG       | Bug fix                                    |
| 📘   | DOCS      | Documentation changes                      |
| 📦   | PyPI      | PyPI releases                              |
| ❤️️   | TEST      | Automated tests                            |
| ⬆️   | CI/CD     | Changes in continuous integration/delivery |
| ⚠️   | SECURITY  | Security improvements                      |

## License

![GitHub License](https://img.shields.io/github/license/dotflow-io/aiflow)

This project is licensed under the terms of the MIT License.
