# Providers

`Provider` (`codeloop.abc.provider.Provider`) is the interface every LLM backend implements. One method:

```python
def complete(
    self,
    system_prompt: str,
    messages: list,
    tools: list[dict],
    on_delta: Callable[[str], None] | None = None,
) -> ProviderResponse:
    ...
```

`ProviderResponse` carries `text`, `tool_calls` (a list of `ToolCall`), `stop_reason`, and `usage` (a `Usage` with `input_tokens`/`output_tokens`).

## Built-in providers

| Provider | Class | Notes |
|----------|-------|-------|
| Anthropic | `codeloop.providers.AnthropicProvider` | Claude models, native streaming and tool use |
| OpenAI | `codeloop.providers.OpenAIProvider` | GPT models; `base_url` makes it work with any OpenAI-compatible server |
| Ollama | `codeloop.providers.OllamaProvider` | `OpenAIProvider` pointed at a local Ollama server by default |
| Generic | `codeloop.providers.GenericProvider` | Any HTTP endpoint; pluggable request/response shape, real SSE streaming |

`GenericProvider` can also be built entirely from a JSON file — no Python required. See [JSON-configured providers](../development/json-provider.md).

## Streaming

When `on_delta` is given, a provider calls it with each text chunk as it arrives instead of only returning the assembled text at the end. Both built-in providers implement this; a provider that can't stream simply ignores `on_delta` and returns the full response in one shot — `Agent` doesn't care either way.

## Swapping providers

Providers are constructed and injected, never selected by a hardcoded switch:

```python
from codeloop import Config
from codeloop.providers import AnthropicProvider, OpenAIProvider

config = Config(provider=AnthropicProvider(model="claude-sonnet-5"))
# or
config = Config(provider=OpenAIProvider(model="gpt-5"))
```

See [Custom providers](../development/custom-provider.md) to bring your own backend, and [Local providers](../development/local-provider.md) for Ollama and other OpenAI-compatible local servers.
