# Release Notes

## v0.3.0

- ⚙️ Ready-made provider templates for Gemini (`templates/gemini.json`), Grok/xAI (`templates/grok.json`), and Groq (`templates/groq.json`) — same `GenericProvider` JSON shape, OpenAI-compatible endpoints, no code required
- ⚙️ VS Code extension (0.3.0): a provider gallery (⚙ → Select Provider…, or `/provider`) replaces the flat quickpick — card picker for Anthropic/OpenAI/Gemini/Grok/Groq/Ollama/LM Studio with a connected/local/needs-key status per card, plus a custom-JSON/generic-URL fallback. API keys are now remembered per provider, so switching back doesn't re-prompt. The panel's visual style was also reworked (thin borders, sharp corners, monospace labels) while staying on VS Code's own theme tokens

## v0.2.1

- ⚙️ VS Code extension source restructured by responsibility — thin `extension.ts` entrypoint, `chatViewProvider.ts` for orchestration, `config/settings.ts` for typed config access, pure `lib/` helpers, and `webview/html.ts` for the panel template — plus 26 unit tests (`npm test`, no new dependency)
- ⚙️ Skills-discovery toggle and MCP server management (add/remove) added to the extension's gear menu and settings, wired into `pycodeloop serve`'s existing `--no-skills`/`--mcp` flags
- ⚙️ Slash commands (`/new`, `/sessions`, `/provider`, `/model`, `/auto-approve`, `/skills`, `/mcp`, `/reload`, `/settings`, `/help`) with an autocomplete dropdown in the extension's prompt box
- 🪲 `Session.history()` self-heals a session left with a dangling `tool_use` (no matching `tool_result`) after the process was killed mid-turn — previously left that conversation permanently rejected by the provider
- 🪲 Extension's CLI-missing detection fixed (was probing `--version`, a flag `pycodeloop` doesn't have) and its auto-install now always installs the CLI globally, matching `pycodeloop.command`'s default of a bare `pycodeloop` resolved off `PATH`

## v0.2.0

- ⚙️ VS Code extension — a sidebar chat panel talking to `pycodeloop serve` over JSON-RPC, with session switching, screenshot/image attachments, auto-approve setting, and Esc-to-cancel
- ⚙️ `pycodeloop serve` — a JSON-RPC-over-stdio server exposing `chat/send`, `chat/cancel`, `chat/confirmResponse`, and `session/list`/`session/load`, plus a `--yes` auto-approve flag, for editor integrations
- ⚙️ `GenericProvider` is now the sole provider implementation — dedicated Anthropic/OpenAI SDK-backed providers were removed in favor of the vendor-agnostic JSON-configured HTTP client
- ⚙️ Agent loop: retries transient provider errors, runs independent tool calls in parallel, auto-compacts older history into the first kept message with tool-result summarization, and a TUI thinking indicator with live context %
- 🪲 Fixed a `CodeLoop` session leak across `session_key` switches and a doubled `pypycodeloop` typo in install docs
- 📘 README and docs updated for the `GenericProvider`-only model; repository moved to `dotflow-io/pycodeloop`

## v0.1.0

Initial release.

- ⚙️ Core agent loop (`Agent`), dependency-injection container (`Config`), conversation state (`Session`), and the `CodeLoop` entrypoint
- ⚙️ `Provider` ABC with `GenericProvider` — any HTTP chat-completions-style API via the stdlib, no vendor SDK, configured declaratively for Anthropic, OpenAI, Ollama, and other backends via JSON (see `templates/`)
- ⚙️ `Tool` ABC with built-in `read_file`, `write_file`, `edit_file`, `delete_file`, `list_dir`, `glob`, `grep`, `bash`, `web_fetch`, `http_request`, `git_status`, `git_diff`, `git_log`, `git_commit`, `env`, `todo`
- ⚙️ Dangerous-tool confirmation gate with diff/command preview
- ⚙️ Streaming text output and per-turn/cumulative token usage tracking
- ⚙️ Auto-compaction of older conversation history and retry with backoff on transient provider failures
- ⚙️ MCP client — connect to any Model Context Protocol server over stdio and use its tools like local ones
- ⚙️ Skills discovery — Claude Code, Cursor, and `AGENTS.md` skills/instructions found on disk are exposed as a `read_skill` tool
- ⚙️ Custom and local providers — dotted-path loading (`module.path:ClassName`) and `base_url` support for any OpenAI-compatible server
- ⚙️ `pycodeloop` CLI (`run`, `chat`, `serve`) with permission prompts, streaming, and token usage reporting — `serve` speaks JSON-RPC over stdio for editor integrations like the VS Code extension
