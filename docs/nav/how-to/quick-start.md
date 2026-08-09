# Quick start

## As a library

```python
from codeloop import CodeLoop, Config
from codeloop.providers import AnthropicProvider

config = Config(provider=AnthropicProvider(model="claude-sonnet-5"))
flow = CodeLoop(config=config)

print(flow.run("list the files in this repo and summarize the project"))
```

## From the CLI

```bash
codeloop run "add a docstring to codeloop/core/agent.py"  # one-shot, scriptable
codeloop                                                 # full-screen Textual TUI (the default with no args)
```

## Low-level: Agent directly

`CodeLoop` is a convenience wrapper. Reach for `Agent` directly when you want per-call control over hooks, tools, or session state:

```python
from codeloop.core.agent import Agent
from codeloop.providers import AnthropicProvider

agent = Agent(
    provider=AnthropicProvider(model="claude-sonnet-5"),
    on_tool_call=lambda name, args: print(f"-> {name} {args}"),
)

reply = agent.run("fix the failing test in tests/test_agent.py")
```

Next: [Streaming](streaming.md), [Permission prompts](permission-prompts.md), [Token usage](token-usage.md).
