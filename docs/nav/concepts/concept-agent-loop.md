# Agent loop

`Agent` (`pycodeloop.core.agent.Agent`) drives a `Provider` through a tool-use loop until the model stops calling tools or `max_turns` is reached:

```
loop until max_turns:
    response = provider.complete(system_prompt, session.history(), tool_schemas)
    if response has no tool_calls:
        return response.text
    for each tool_call:
        confirm it if the tool is dangerous
        run it, feed the result back into the session
```

Each iteration:

1. Sends the system prompt, the full conversation history (`Session`), and the JSON schema of every available tool to the provider.
2. If the provider returns plain text with no tool calls, the loop ends and that text is the result.
3. If the provider returns tool calls, each one is executed (after a confirmation gate for `dangerous` tools) and its result is appended to the session as a `tool` message, then the loop goes around again — the model sees the tool output on the next turn.

## Hooks

`Agent` accepts optional callbacks so a caller (like the CLI) can observe or intervene without subclassing anything:

| Hook | Signature | When it fires |
|------|-----------|----------------|
| `on_request` | `(message_count, tool_count)` | Right before each provider call |
| `on_tool_call` | `(name, arguments)` | Right before a tool call is attempted |
| `on_tool_result` | `(name, result_text, is_error)` | After a tool call finishes (or is declined) |
| `on_text_delta` | `(chunk)` | For every streamed text chunk, if the provider supports streaming |
| `confirm` | `(name, preview) -> bool \| str` | Before a `dangerous` tool runs; `False`/a string skips it |
| `on_usage` | `(turn_usage, total_usage, elapsed)` | After every provider call, with per-turn/running token totals and wall-clock seconds |
| `on_context` | `(used_tokens, limit_tokens)` | After every provider call, with context-window usage |
| `on_compact_start` | `()` | When auto-compaction of older history begins |
| `on_compact_end` | `(before_count, after_count)` | When auto-compaction finishes, with message counts before/after |
| `on_retry` | `(attempt, delay, exc)` | Before retrying a transient provider failure (rate limits, 5xx, network errors) |
| `on_message` | `()` | After every message (user/assistant/tool) is appended to the session — used to persist incrementally |

`Agent` also retries transient provider failures (HTTP 408/429/500/502/503/504, timeouts, connection errors) up to 3 times with exponential backoff before raising, and auto-compacts older history via a provider-generated summary once context usage crosses `compact_threshold` (default `0.8`) of the model's context window.

See [Streaming](../how-to/streaming.md), [Permission prompts](../how-to/permission-prompts.md), and [Token usage](../how-to/token-usage.md) for how the CLI wires these up.
