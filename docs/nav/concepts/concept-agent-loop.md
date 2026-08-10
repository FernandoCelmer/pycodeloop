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
| `on_tool_call` | `(name, arguments)` | Right before a tool call is attempted |
| `on_tool_result` | `(name, result_text)` | After a tool call finishes (or is declined) |
| `on_text_delta` | `(chunk)` | For every streamed text chunk, if the provider supports streaming |
| `confirm` | `(name, preview) -> bool` | Before a `dangerous` tool runs; declining skips it |
| `on_usage` | `(turn_usage, total_usage)` | After every provider call, with per-turn and running token totals |

See [Streaming](../how-to/streaming.md), [Permission prompts](../how-to/permission-prompts.md), and [Token usage](../how-to/token-usage.md) for how the CLI wires these up.
