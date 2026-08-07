# Quick start

## As a library

```python
from aiflow import AIFlow, Config
from aiflow.providers import AnthropicProvider

config = Config(provider=AnthropicProvider(model="claude-sonnet-5"))
flow = AIFlow(config=config)

print(flow.run("list the files in this repo and summarize the project"))
```

## From the CLI

```bash
aiflow run "add a docstring to aiflow/core/agent.py"
aiflow chat   # plain-terminal interactive session
aiflow        # full-screen Textual TUI (the default with no args)
```

## Low-level: Agent directly

`AIFlow` is a convenience wrapper. Reach for `Agent` directly when you want per-call control over hooks, tools, or session state:

```python
from aiflow.core.agent import Agent
from aiflow.providers import AnthropicProvider

agent = Agent(
    provider=AnthropicProvider(model="claude-sonnet-5"),
    on_tool_call=lambda name, args: print(f"-> {name} {args}"),
)

reply = agent.run("fix the failing test in tests/test_agent.py")
```

Next: [Streaming](streaming.md), [Permission prompts](permission-prompts.md), [Token usage](token-usage.md).
