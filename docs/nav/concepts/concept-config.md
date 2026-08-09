# Config (dependency injection)

`Config` (`codeloop.core.config.Config`) is a small dependency-injection container — build one, hand it a `Provider` and a tool set, pass it to `CodeLoop`:

```python
config = Config(
    provider=AnthropicProvider(model="claude-sonnet-5"),
    tools=DEFAULT_TOOLS,
    system_prompt="You are a terse code reviewer.",
    max_turns=25,
)
```

| Arg | Default | Purpose |
|-----|---------|---------|
| `provider` | resolved from `CODELOOP_PROVIDER`/`CODELOOP_MODEL` env vars | LLM backend driving the agent |
| `tools` | `DEFAULT_TOOLS` | Tools exposed to the agent |
| `system_prompt` | `Agent.DEFAULT_SYSTEM_PROMPT` | Overrides the default instructions |
| `max_turns` | `25` (or `CODELOOP_MAX_TURNS`) | Hard cap on tool-use loop iterations |

`Config.__init__` validates that `provider` is an instance of the `Provider` ABC and raises `NotProviderInstance` immediately if not — a wrong object fails at construction time, not three tool calls into a run.

## Default provider resolution

If `provider` is omitted, `Config` resolves one from `codeloop.settings.Settings`, which reads:

- `CODELOOP_PROVIDER` — `anthropic` (default), `openai`, `ollama`, or a `module.path:ClassName` for a custom provider
- `CODELOOP_MODEL` — overrides the provider's default model
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` — read automatically based on `CODELOOP_PROVIDER`

## CodeLoop: Config + Agent + Session

`CodeLoop` (`codeloop.core.codeloop.CodeLoop`) is a thin wrapper: it takes a `Config`, builds the `Agent` and a `Session`, and exposes `.run(prompt)` that keeps conversation history across calls.

```python
from codeloop import CodeLoop, Config
from codeloop.providers import AnthropicProvider

flow = CodeLoop(Config(provider=AnthropicProvider(model="claude-sonnet-5")))
flow.run("what does this repo do?")
flow.run("now add a test for it")  # remembers the first turn
```
