# Agent Instructions — pycodeloop / aiflow

Standing rules for any agent (CodeLoop, Claude Code, or otherwise) working
in this repo. Read this before making changes — it captures corrections
already given more than once; don't make the user repeat them.

## Code

- No comments unless they explain a non-obvious *why* (a hidden constraint,
  a workaround, a subtle invariant). Never restate what the code already
  says.
- No speculative abstractions, feature flags, or error handling for cases
  that can't happen. Smallest change that solves the actual request.
- `write_file`/`edit_file` content is literal file text, never diff syntax
  — no `@@ ... @@` hunks, no leading `-`/`+` line markers.

## Providers (`templates/`, `pycodeloop/providers/templates/`)

- These two directories must stay in sync — a new or changed provider JSON
  goes in both, or the CLI and the docs disagree about what's available.
  The VS Code extension (see below) keeps its own copy in a separate repo
  and its own multi-model catalog — keep that in sync too when a model
  list changes.
- Before naming a model ID or endpoint, verify it against current vendor
  docs (WebFetch/WebSearch) — don't guess or reuse a remembered ID.
  Model catalogs (OpenAI, Gemini, Grok, Groq, ...) churn fast; a name that
  was right last month can 404 today.
- `templates/openai.json`, `.../gemini.json`, etc. only carry one default
  `model` each — a multi-choice picker only exists in the VS Code
  extension's own provider catalog.

## VS Code extension

Lives in its own repo, [dotflow-io/vscodeloop](https://github.com/dotflow-io/vscodeloop)
— not in this one. See that repo's own `AGENTS.md` for its conventions
(UI style, no-emoji-icons rule, `.vsix` rebuild/reinstall steps).

## Commits

- Only commit when explicitly asked.
- Follow the icon+TYPE convention in the root `README.md` → *Commit
  Style* table (`⚙️ FEATURE`, `🪲 BUG`, `📘 DOCS`, `📦 Release`/`PyPI`,
  `🎨 STYLE`, `❤️ TEST`, ...). Look at recent `git log` output for the
  exact tone/format, not just the table.
- One logical change per commit — don't bundle an unrelated fix into a
  feature commit just because they happened in the same session.
- Never `git add -A`/`-u`; stage files by name. Flag any untracked files
  that look unrelated to the current task instead of committing them
  blindly.

## Testing

- Python: `pytest -q` from repo root (venv at `.venv/`).
- Must pass before calling anything finished.
