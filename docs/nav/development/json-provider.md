# JSON-configured providers

For an HTTP LLM API, you don't need to write a `Provider` subclass at all — point `--provider` at a JSON file instead.

## Example

[`provider.example.json`](../../examples/provider.example.json):

```json
{
  "url": "https://api.example.com/v1/chat/completions",
  "model": "my-model",
  "api_key_env": "MY_API_KEY",
  "headers": {
    "X-Org": "acme"
  },
  "timeout": 60,
  "response_paths": {
    "text": "choices.0.message.content",
    "tool_calls": "choices.0.message.tool_calls",
    "stop_reason": "choices.0.finish_reason",
    "input_tokens": "usage.prompt_tokens",
    "output_tokens": "usage.completion_tokens",
    "tool_call_id": "id",
    "tool_call_name": "function.name",
    "tool_call_arguments": "function.arguments"
  }
}
```

```bash
pycodeloop run "list the files here" --provider ./provider.example.json
```

Or as a library:

```python
from pycodeloop.providers import get_provider

provider = get_provider("./provider.example.json")
```

## Fields

| Field | Required | Purpose |
|-------|----------|---------|
| `url` | Yes | Endpoint that receives the chat-completions POST request |
| `model` | No | Sent as `"model"` in the request body |
| `api_key` | No | Literal key, sent as `Authorization: Bearer <key>` |
| `api_key_env` | No | Env var name to read the key from instead of a literal in the file |
| `headers` | No | Extra headers merged into every request |
| `timeout` | No | Request timeout in seconds (default `60`) |
| `response_paths` | No | Remaps the response shape — see below |

`--model` and the provider's own `*_API_KEY` env var (from `--provider`'s resolution) still override `model`/`api_key` from the file when passed explicitly on the CLI.

## response_paths

The request body always uses the OpenAI chat-completions shape. If the API's **response** also matches that shape (`choices[0].message.content`, `usage.prompt_tokens`, ...), omit `response_paths` entirely — that's the default.

If the response has a different shape, `response_paths` maps each field with a dot-path into the JSON response (list indices are plain numbers, e.g. `choices.0.message.content`):

| Key | Default | Points at |
|-----|---------|-----------|
| `text` | `choices.0.message.content` | The reply text |
| `tool_calls` | `choices.0.message.tool_calls` | List of tool calls |
| `stop_reason` | `choices.0.finish_reason` | Why the turn ended |
| `input_tokens` | `usage.prompt_tokens` | Input token count |
| `output_tokens` | `usage.completion_tokens` | Output token count |
| `tool_call_id` | `id` | *(within each tool call)* its id |
| `tool_call_name` | `function.name` | *(within each tool call)* its name |
| `tool_call_arguments` | `function.arguments` | *(within each tool call)* its arguments — a JSON string or an object, either works |

### Example: a non-OpenAI-shaped API

```json
{
  "url": "https://api.example.com/answer",
  "model": "my-model",
  "response_paths": {
    "text": "result.answer",
    "input_tokens": "meta.tokens_in",
    "output_tokens": "meta.tokens_out"
  }
}
```

A response like `{"result": {"answer": "hi"}, "meta": {"tokens_in": 7, "tokens_out": 4}}` resolves to `text="hi"`, `input_tokens=7`, `output_tokens=4` — no Python required.

For anything `response_paths` can't express (custom auth flow, non-JSON body, SSE with a different shape), drop down to a real [custom provider](custom-provider.md) instead.

## Ready-made templates

[`templates/`](../../../templates) has configs for common backends — point `--provider` straight at one, or copy it as a starting point:

| Template | Backend |
|----------|---------|
| [`anthropic.json`](../../../templates/anthropic.json) | Anthropic's native Messages API (not the OpenAI-compatible one) |
| [`openai.json`](../../../templates/openai.json) | OpenAI directly |
| [`ollama.json`](../../../templates/ollama.json) | Local [Ollama](https://ollama.com) (`ollama serve`, no API key) |
| [`lmstudio.json`](../../../templates/lmstudio.json) | Local [LM Studio](https://lmstudio.ai) server (no API key) |
| [`reference.json`](../../../templates/reference.json) | Every field below, with its default/example value — not meant to be run as-is |

```bash
pycodeloop run "..." --provider templates/ollama.json
```

Local ones (Ollama, LM Studio) have no `api_key`/`api_key_env` — `GenericProvider` only sends an `Authorization` header when a key is actually present, so it's simply omitted.

## Talking to a non-OpenAI-shaped API: Anthropic's native format

The request body defaults to the OpenAI chat-completions shape. For a backend that speaks a genuinely different shape — like Anthropic's own Messages API, which [`templates/anthropic.json`](../../../templates/anthropic.json) targets — set both the outgoing request shape and the incoming response shape:

```json
{
  "url": "https://api.anthropic.com/v1/messages",
  "model": "claude-sonnet-5",
  "api_key_env": "ANTHROPIC_API_KEY",
  "auth_header": "x-api-key",
  "auth_prefix": "",
  "headers": { "anthropic-version": "2023-06-01" },
  "request": {
    "body_paths": { "system": "system" },
    "message_shape": "anthropic",
    "tool_schema": "anthropic",
    "params": { "max_tokens": 1024 }
  },
  "response_shape": "anthropic"
}
```

| `request.*` field | Purpose |
|---|---|
| `message_shape: "anthropic"` | Build each message the way Anthropic expects (content blocks, `tool_use`/`tool_result` instead of OpenAI's `tool_calls`/`role: "tool"`) |
| `tool_schema: "anthropic"` | Describe tools as `{name, description, input_schema}` instead of OpenAI's `{type: "function", function: {...}}` |
| `body_paths.system` | Move the system prompt to its own top-level body key (`"system"`) instead of embedding it as the first message — Anthropic requires this |
| `params` | Extra static fields merged into every request body — Anthropic requires `max_tokens`, since it has no default |

`response_shape: "anthropic"` parses replies from `content[]` blocks (`type: "text"`/`"tool_use"`) instead of `choices[0].message`, and usage from `usage.input_tokens`/`usage.output_tokens` instead of `usage.prompt_tokens`/`usage.completion_tokens`.

`auth_header`/`auth_prefix` also differ from the OpenAI-style default (`Authorization: Bearer <key>`) — Anthropic wants the raw key in `x-api-key` with no prefix, which is why both are overridden above.
