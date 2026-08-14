# Config (dependency injection)

`Config` (`pycodeloop.core.config.Config`) is a small dependency-injection container — build one, hand it a `Provider` and a tool set, pass it to `CodeLoop`:

```python
config = Config(
    provider=GenericProvider.from_json("templates/anthropic.json"),
    tools=DEFAULT_TOOLS,
    system_prompt="You are a terse code reviewer.",
    max_turns=25,
)
```

| Arg | Default | Purpose |
|-----|---------|---------|
| `provider` | resolved from `PYCODELOOP_PROVIDER`/`PYCODELOOP_MODEL` env vars | LLM backend driving the agent |
| `tools` | `DEFAULT_TOOLS` | Tools exposed to the agent |
| `system_prompt` | `pycodeloop.core.agent.DEFAULT_SYSTEM_PROMPT` | Overrides the default instructions |
| `max_turns` | `25` (or `PYCODELOOP_MAX_TURNS`) | Hard cap on tool-use loop iterations |
| `max_history_turns` | `20` | Cap the session on the number of most recent user-initiated turns kept before each provider call; pass `None` for unbounded growth |
| `skills` | `False` | Discover Claude Code/Cursor/`AGENTS.md` skills on disk, expose a `read_skill` tool, and list them in the system prompt |
| `skill_sources` | all sources | Limit discovery to a subset (`"claude-skill"`, `"claude-memory"`, `"cursor-rule"`, `"agents-md"`) |
| `skills_refresh` | `False` | Skip the skills cache and force a full rescan |
| `delegation` | `False` | Expose a `delegate` tool that spawns a fresh sub-agent (same provider, read-only tools) for an independent subtask. Several `delegate` calls in the same turn run in parallel |
| `memory` | `True` | Load `.pycodeloop/memory.md` into the system prompt and expose a `remember` tool the agent uses to save standing corrections/preferences across sessions |
| `storage` | `SqliteSessions()` (`~/.pycodeloop/pycodeloop.db`) | Persists sessions so `CodeLoop.run(prompt, session_key=...)` can resume across restarts; pass `False` for in-memory only |

`Config.__init__` validates that `provider` is an instance of the `Provider` ABC and raises `NotProviderInstance` immediately if not — a wrong object fails at construction time, not three tool calls into a run.

## Default provider resolution

If `provider` is omitted, `Config` resolves one from `pycodeloop.settings.Settings`, which reads:

- `PYCODELOOP_PROVIDER` — a path to a JSON config file (a bundled `templates/anthropic.json`-equivalent is the default), the bare string `"generic"` paired with an explicit `url=`, or a `module.path:ClassName` for a custom provider
- `PYCODELOOP_MODEL` — overrides the model named in the JSON config (or passed to a custom provider)
- The API key env var named by the JSON config's own `api_key_env` field (`ANTHROPIC_API_KEY` for the bundled default) — read automatically, no separate `PYCODELOOP_*` var needed

## CodeLoop: Config + Agent + Session

`CodeLoop` (`pycodeloop.core.codeloop.CodeLoop`) is a thin wrapper: it takes a `Config`, builds the `Agent` and a `Session`, and exposes `.run(prompt)` that keeps conversation history across calls.

```python
from pycodeloop import CodeLoop, Config
from pycodeloop.providers import GenericProvider

flow = CodeLoop(Config(provider=GenericProvider.from_json("templates/anthropic.json")))
flow.run("what does this repo do?")
flow.run("now add a test for it")  # remembers the first turn
```
