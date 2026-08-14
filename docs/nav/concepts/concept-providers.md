# Providers

`Provider` (`pycodeloop.abc.provider.Provider`) is the interface every LLM backend implements. One method:

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

## GenericProvider: the only provider class

`pycodeloop.providers.GenericProvider` is the sole `Provider` implementation CodeLoop ships — any HTTP chat-completions-style API, driven by the stdlib (`urllib`), no vendor SDK. There's no separate `AnthropicProvider`/`OpenAIProvider`/`OllamaProvider`; every vendor is just a different `GenericProvider` configuration.

It can be built three ways:

1. **From a JSON config file** — the standard way, no Python required:

   ```python
   from pycodeloop.providers import GenericProvider

   provider = GenericProvider.from_json("templates/anthropic.json")
   ```

2. **Ad hoc**, with `url`/`model` kwargs and no config file — for a quick OpenAI-compatible endpoint:

   ```python
   from pycodeloop.providers import get_provider

   provider = get_provider("generic", url="http://localhost:8000/v1/chat/completions", model="my-model")
   ```

3. **A fully custom `Provider` subclass**, loaded by dotted path — see [Custom providers](../development/custom-provider.md).

`pycodeloop.providers.get_provider(name, **kwargs)` picks between the three based on `name`: a path ending in `.json` loads a config file, the literal string `"generic"` builds one ad hoc from kwargs, and anything containing `:` is treated as `'module.path:ClassName'`.

## JSON config shape

A config file (see [`templates/`](https://github.com/dotflow-io/pycodeloop/tree/master/templates) for ready-made ones — `anthropic.json`, `openai.json`, `gemini.json`, `grok.json`, `groq.json`, `ollama.json`, `lmstudio.json` — and [`reference.json`](https://github.com/dotflow-io/pycodeloop/blob/master/templates/reference.json) for every field) declares:

- `url`, `model`, `api_key`/`api_key_env`, `headers`, `auth_header`/`auth_prefix`, `timeout` — connection basics.
- `response_shape: "anthropic"` — a one-word override that parses replies from Anthropic's `content[]` blocks and `usage.input_tokens`/`usage.output_tokens` instead of the OpenAI-shaped `choices[0].message`/`usage.prompt_tokens`. Omit it (or use `response_paths`, a dict of dot-paths into an arbitrary JSON response) for anything else non-OpenAI-shaped.
- `request.message_shape`/`request.tool_schema`, each `"openai"` (default) or `"anthropic"` — how outgoing messages and tool definitions are built. `"anthropic"` produces content blocks and `tool_use`/`tool_result` instead of OpenAI's `tool_calls`/`role: "tool"`, and `{name, description, input_schema}` tool defs instead of `{type: "function", function: {...}}`.
- `request.params` — extra static fields merged into every request body (e.g. Anthropic's required `max_tokens`). `request.params_key` nests `params` under a single body key instead of merging them at the top level; `request.extra_body` is always merged in last, at the top level of the body.
- `request.body_paths` — renames/relocates outgoing body keys (`system` moves the system prompt to its own top-level field instead of the first message; `message_role`/`message_content` rename per-message keys).

See [JSON-configured providers](../development/json-provider.md) for the full field reference and worked examples, including the Anthropic-shaped config above.

A provider built via `from_json` can also `reload()` — re-reads the file and applies `url`/`model`/`headers`/etc in place, so a running session picks up an edited config (e.g. a different `model`) without restarting.

## Streaming

When `on_delta` is given, `complete()` calls it with each text chunk as it arrives instead of only returning the assembled text at the end. `GenericProvider` streams real SSE chunks for the default OpenAI chat-completions shape; a config with a custom `response_shape`/`response_paths` still accepts `on_delta`, but delivers the full text as one chunk once the response completes rather than token-by-token.

## Swapping providers

Providers are constructed and injected, never selected by a hardcoded switch:

```python
from pycodeloop import Config
from pycodeloop.providers import GenericProvider

config = Config(provider=GenericProvider.from_json("templates/anthropic.json"))
# or
config = Config(provider=GenericProvider.from_json("templates/openai.json"))
```

See [Custom providers](../development/custom-provider.md) to bring your own backend, and [Local providers](../development/local-provider.md) for Ollama and other OpenAI-compatible local servers.
