# Quick start

## As a library

```python
from pycodeloop import CodeLoop, Config
from pycodeloop.providers import GenericProvider

config = Config(provider=GenericProvider.from_json("templates/anthropic.json"))
flow = CodeLoop(config=config)

print(flow.run("list the files in this repo and summarize the project"))
```

## From the CLI

```bash
pycodeloop run "add a docstring to pycodeloop/core/agent.py"  # one-shot, scriptable
pycodeloop                                                 # full-screen chat (the default with no args)
```

## Low-level: Agent directly

`CodeLoop` is a convenience wrapper. Reach for `Agent` directly when you want per-call control over hooks, tools, or session state:

```python
from pycodeloop.core.agent import Agent
from pycodeloop.providers import GenericProvider

agent = Agent(
    provider=GenericProvider.from_json("templates/anthropic.json"),
    on_tool_call=lambda name, args: print(f"-> {name} {args}"),
)

reply = agent.run("fix the failing test in tests/test_agent.py")
```

Next: [Streaming](streaming.md), [Permission prompts](permission-prompts.md), [Token usage](token-usage.md).
