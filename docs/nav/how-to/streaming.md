# Streaming

Pass `on_text_delta` to `Agent` and it's called with each chunk of text as the model generates it, instead of only getting the assembled reply at the end:

```python
from pycodeloop.core.agent import Agent
from pycodeloop.providers import AnthropicProvider

agent = Agent(
    provider=AnthropicProvider(model="claude-sonnet-5"),
    on_text_delta=lambda chunk: print(chunk, end="", flush=True),
)

agent.run("explain what this codebase does")
```

Both built-in providers (`AnthropicProvider`, `OpenAIProvider`) stream natively — Anthropic via `client.messages.stream(...)`, OpenAI via `stream=True`. If `on_text_delta` is `None` (the default), providers skip streaming entirely and return the full response in one call.

## In the CLI

`pycodeloop run` and the TUI always stream — the reply prints as it arrives, matching a terminal coding agent's feel rather than waiting on a spinner.
