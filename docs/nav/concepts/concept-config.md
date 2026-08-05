# Config (dependency injection)

`Config` (`aiflow.core.config.Config`) is a small DI container — the same role dotflow's `Config` plays for `Storage`/`Notify`/`Log`:

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
| `provider` | resolved from `AIFLOW_PROVIDER`/`AIFLOW_MODEL` env vars | LLM backend driving the agent |
| `tools` | `DEFAULT_TOOLS` | Tools exposed to the agent |
| `system_prompt` | `Agent.DEFAULT_SYSTEM_PROMPT` | Overrides the default instructions |
| `max_turns` | `25` (or `AIFLOW_MAX_TURNS`) | Hard cap on tool-use loop iterations |

`Config.__init__` validates that `provider` is an instance of the `Provider` ABC and raises `NotProviderInstance` immediately if not — a wrong object fails at construction time, not three tool calls into a run.

## Default provider resolution

If `provider` is omitted, `Config` resolves one from `aiflow.settings.Settings`, which reads:

- `AIFLOW_PROVIDER` — `anthropic` (default), `openai`, `ollama`, or a `module.path:ClassName` for a custom provider
- `AIFLOW_MODEL` — overrides the provider's default model
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` — read automatically based on `AIFLOW_PROVIDER`

## AIFlow: Config + Agent + Session

`AIFlow` (`aiflow.core.aiflow.AIFlow`) is a thin wrapper: it takes a `Config`, builds the `Agent` and a `Session`, and exposes `.run(prompt)` that keeps conversation history across calls.

```python
from aiflow import AIFlow, Config
from aiflow.providers import AnthropicProvider

flow = AIFlow(Config(provider=AnthropicProvider(model="claude-sonnet-5")))
flow.run("what does this repo do?")
flow.run("now add a test for it")  # remembers the first turn
```
