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
codeloop run "list the files here" --provider ./provider.example.json
```

Or as a library:

```python
from codeloop.providers import get_provider

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
