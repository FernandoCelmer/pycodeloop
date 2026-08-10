# Token usage

Every `ProviderResponse` carries a `Usage(input_tokens, output_tokens)`. `Agent` accumulates it across the whole run and exposes both the per-turn delta and the running total through the `on_usage` hook:

```python
from pycodeloop.core.agent import Agent

agent = Agent(
    provider=provider,
    on_usage=lambda turn, total: print(
        f"turn: {turn.input_tokens} in / {turn.output_tokens} out "
        f"(total: {total.input_tokens} in / {total.output_tokens} out)"
    ),
)

agent.run("...")
print(agent.usage)  # Usage(input_tokens=..., output_tokens=...) — cumulative for this Agent
```

`agent.usage` persists across multiple `agent.run(...)` calls on the same `Agent` instance — it's a running session total, not reset per call.

## In the CLI

`pycodeloop run` and the chat print the running total after every turn:

```
🤖 1.2k in / 340 out
```
