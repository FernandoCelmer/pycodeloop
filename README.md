<div align="center">

**Bring your own model. Swap providers. Ship an agent.**

[![PyPI](https://img.shields.io/pypi/v/aiflow?style=flat-square)](https://pypi.org/project/aiflow/)
[![Python](https://img.shields.io/pypi/pyversions/aiflow?style=flat-square)](https://pypi.org/project/aiflow/)
[![Stars](https://img.shields.io/github/stars/dotflow-io?label=Stars&style=flat-square)](https://github.com/dotflow-io/aiflow)

[Repository](https://github.com/dotflow-io/aiflow)

</div>

---

# AIFlow

AIFlow is a lightweight Python library for building agentic coding assistants — in the shape of Claude Code, Codex, or Gemini CLI. Give it a provider and a prompt, it drives a tool-use loop (read, write, edit, grep, bash) until the task is done. Same shape everywhere: swap Anthropic for OpenAI without touching the agent loop.

## Why AIFlow?

- **Simple** — `AIFlow(config=Config(...)).run("do the thing")`. That's it.
- **Multi-provider** — Anthropic and OpenAI ship built-in. Add any LLM backend by implementing one interface.
- **Decoupled** — providers are injected, not hardcoded. Swap them the same way dotflow swaps `Storage`/`Notify`/`Log`.
- **Embeddable** — use it as a library inside your own app, or drive it from the `aiflow` CLI.
- **Extensible tools** — read/write/edit/list/grep/bash out of the box; add your own by subclassing `Tool`.

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

The `Config` class validates and injects the pieces an agent run needs — same pattern dotflow uses for `Storage`/`Notify`/`Log`:

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
| `list_dir` | List a directory |
| `grep` | Regex search across files |
| `bash` | Run a shell command with a timeout |

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

---

</details>

<details>
<summary><strong>CLI</strong></summary>

Run the agent directly from the command line:

```bash
# One-shot
aiflow run "add a docstring to aiflow/core/agent.py"

# Interactive session, conversation history kept across turns
aiflow chat

# Override provider/model per invocation
aiflow run "..." --provider openai --model gpt-5
```

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
