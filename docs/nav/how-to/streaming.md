# Streaming

Pass `on_text_delta` to `Agent` and it's called with each chunk of text as the model generates it, instead of only getting the assembled reply at the end:

```python
from pycodeloop.core.agent import Agent
from pycodeloop.providers import GenericProvider

agent = Agent(
    provider=GenericProvider.from_json("templates/openai.json"),
    on_text_delta=lambda chunk: print(chunk, end="", flush=True),
)

agent.run("explain what this codebase does")
```

`GenericProvider` streams real SSE chunks for the default OpenAI chat-completions request/response shape — a config like `templates/openai.json` or `templates/ollama.json` that doesn't override `response_shape`/`response_paths`. A config with a custom response shape (e.g. `templates/anthropic.json`, which sets `response_shape: "anthropic"`) still works with `on_text_delta`, but delivers the full text as a single chunk once the request completes rather than token-by-token. If `on_text_delta` is `None` (the default), providers skip streaming entirely and return the full response in one call.

## In the CLI

`pycodeloop run` and the chat always stream — the reply prints as it arrives, matching a terminal coding agent's feel rather than waiting on a spinner.
