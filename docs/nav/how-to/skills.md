# Skills

CodeLoop can discover skills already sitting on disk from other tools and expose them to the agent — no separate setup, it reads what Claude Code, Cursor, or your project's `AGENTS.md` already have.

## What gets scanned

| Source | Locations |
|--------|-----------|
| `claude-skill` | `~/.claude/skills/*/SKILL.md`, `./.claude/skills/*/SKILL.md` |
| `claude-memory` | `~/.claude/CLAUDE.md`, `./CLAUDE.md` |
| `cursor-rule` | `./.cursor/rules/*.mdc`, `./.cursorrules` |
| `agents-md` | `./AGENTS.md` |

Each match becomes a `Skill` (`pycodeloop.core.skills.Skill`): a name, a short description, its source, and the full content, read lazily.

## As a library

```python
from pycodeloop import Config
from pycodeloop.providers import AnthropicProvider

config = Config(
    provider=AnthropicProvider(model="claude-sonnet-5"),
    skills=True,
)
print([s.name for s in config.skills])
```

When `skills=True`, `Config` appends a `read_skill` tool to the tool set and lists every discovered skill's name and description in the system prompt, so the agent knows what's available and can pull the full content in on demand instead of every skill being stuffed into context up front.

Narrow discovery to specific sources with `skill_sources`:

```python
config = Config(provider=..., skills=True, skill_sources={"agents-md"})
```

## From the CLI

On by default for both `run` and `chat`:

```bash
pycodeloop run "..."              # skills discovered automatically
pycodeloop run "..." --no-skills  # turn it off
```

## Caching

Discovery results are cached in `~/.pycodeloop/config.json`, keyed by each file's path and mtime — unchanged skills aren't re-read on the next run. `--skills-refresh` (or `discover_skills(..., use_cache=False)` as a library) bypasses the cache and forces a full rescan.
