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

## Providers (`templates/`, `pycodeloop/providers/templates/`,
## `vscode-extension/providers/`)

- These three directories must stay in sync — a new or changed provider
  JSON goes in all three, or the CLI/docs and the extension disagree about
  what's available.
- Before naming a model ID or endpoint, verify it against current vendor
  docs (WebFetch/WebSearch) — don't guess or reuse a remembered ID.
  Model catalogs (OpenAI, Gemini, Grok, Groq, ...) churn fast; a name that
  was right last month can 404 today.
- `templates/openai.json`, `.../gemini.json`, etc. only carry one default
  `model` each — the multi-choice list lives in
  `vscode-extension/src/lib/providerCatalog.ts`.

## VS Code extension (`vscode-extension/`)

- UI style: thin 1px borders, sharp corners (`border-radius: 0` except
  circular status dots), monospace + uppercase for chrome/buttons, all
  colors via `var(--vscode-*)` tokens (never hardcode hex — the panel must
  follow the user's editor theme, light or dark).
- No emoji as icons. Buttons are plain uppercase text unless there's
  genuinely no room for a label (e.g. the Settings gear) — then a thin
  inline stroke SVG (`stroke="currentColor"`, no fill), never a Unicode
  symbol.
- After *any* change under `vscode-extension/`, before saying the work is
  done:
  1. `npm run test` (must pass)
  2. `rm -f pycodeloop-*.vsix && npx --no-install vsce package`
  3. `code --uninstall-extension fernandocelmer.pycodeloop && code --install-extension pycodeloop-<version>.vsix`
  A stale installed `.vsix` is the single most common source of "the fix
  didn't work" confusion — always reinstall, don't assume the last build
  is what's running.

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
- Extension: `npm run test` from `vscode-extension/` (compiles + runs
  `node --test`).
- Both must pass before calling anything finished.
