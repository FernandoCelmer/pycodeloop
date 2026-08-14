# Release Notes

## v0.4.0

**pycodeloop core**

- ⚙️ Sub-agent delegation (`--delegate`, off by default) — a `delegate` tool spawns a fresh sub-agent (same provider, read-only tools: `read_file`/`list_dir`/`glob`/`grep`/`git status`/`diff`/`log`/`web_fetch`/`sql_schema`/`sql_query`, no write/edit/delete/bash) for an independent subtask. Several `delegate` calls in the same turn run in parallel
- 🪲 `Agent._can_parallelize` previously forced *any* repeated tool name in a batch to run sequentially, even for stateless tools — added `Tool.concurrent_safe` (opt-in, default `False`, preserves existing behavior for every built-in tool) so `delegate` can declare its repeated calls safe to run concurrently
- ⚙️ Persistent project memory (`--memory`, on by default) — `.pycodeloop/memory.md` auto-loaded into the system prompt every run, plus a `remember` tool the agent calls when the user corrects its approach or states a standing rule. `remember` is gated behind confirmation like every other write tool
- 🪲 `write_file`/`edit_file` reject content that looks like a pasted unified diff (`@@ ... @@` hunk header, or `---`/`+++` file headers) instead of writing the diff syntax itself into the file
- ⚙️ Six more ready-made provider templates: AWS Bedrock (`aws.json`, via the bearer-token `bedrock-mantle` endpoint — no SigV4 needed), Kimi/Moonshot AI (`kimi.json`), DeepSeek (`deepseek.json`), Llama via Together AI (`llama.json` — Meta retired its own Llama API on 2026-07-06), Qwen/Alibaba DashScope (`qwen.json`), NVIDIA NIM (`nvidia.json`)
- 🪲 Grok template was pointing at `grok-4`/`grok-4-fast`/`grok-code-fast-1` — all retired 2026-05-15. Moved to `grok-4.5`/`grok-4.3`/`grok-build-0.1`. OpenAI template's `gpt-5`/`gpt-5-mini`/`gpt-5-nano` moved to the current `gpt-5.6` family
- 🪲 Gemini 3's thinking models attach `extra_content.google.thought_signature` to tool_calls and reject the next turn if it isn't echoed back unchanged — and thinking can't be disabled on Gemini 3 (minimum is `LOW`, which still requires the signature). Rather than staying pinned to Gemini 2.5 (itself now 404ing for new API keys), `GenericProvider` round-trips arbitrary vendor-specific tool_call fields via a new `ToolCall.extra`, so Gemini's default is `gemini-3.6-flash` again
- ⚙️ Anthropic prompt caching — set `"prompt_cache": true` in a provider's `request` config (already on by default in `anthropic.json`) to mark the system prompt and the last tool definition with `cache_control: {"type": "ephemeral"}`, so Anthropic reuses the cached system prompt + tool schema across turns instead of reprocessing them every request (cache reads cost ~10% of a normal input token)
- ⚙️ Two new tools: `sql_schema` (list a database's tables, or one table's columns) and `sql_query` (a single read-only SELECT/WITH/EXPLAIN/PRAGMA/SHOW/DESCRIBE statement, no writes/DDL/stacked statements) — any SQLAlchemy-supported database via a connection URL
- ⚙️ Token-saving read cache — `read_file` now logs every read/write/edit/delete to a `file_access` table (`~/.pycodeloop/pycodeloop.db`), scoped to the session. Reading the exact same path/offset/limit twice with no change on disk in between returns a short "unchanged since you last read" notice instead of repeating the content — pass `force=true` to see it again
- 🗑️ Removed the `todo` tool (scratchpad checklist) — never adopted, dead weight in the default tool list
- 🪲 `http_request`/`web_fetch` had a DNS-rebinding gap in their SSRF guard: the hostname was resolved once to check it wasn't private/internal, then resolved *again*, independently, for the actual connection — a rebinding DNS answer between those two lookups could hand the request to a blocked address the check had just approved. Both now resolve once and connect directly to that pinned address (`Host` header + TLS SNI still carry the real hostname, so routing/cert validation are unaffected)
- 🪲 `git_diff`/`git_log`/etc never capped their output, unlike every other tool (`bash`, filesystem, `grep`, `http_request`, `web_fetch`) — a large diff or a deep log could blow out the context. `http_request`/`web_fetch` also each hand-rolled the same 20000-char truncation `_limits.truncate()` already provides; both now use it
- 🪲 `env` now also masks values shaped like `scheme://user:pass@host` (e.g. a `DATABASE_URL`), not just names containing SECRET/KEY/TOKEN/PASSWORD/CREDENTIAL; `grep` skips binary files instead of searching through decoded garbage
- 🎨 `core/` split: `store/` (SQLite/JSON/file sessions, usage tracking, user settings, ORM models), `tools/` (built-in `Tool` implementations — the `Tool` ABC already lived in `abc/`, not `core/`), and the optional-feature modules `skills.py`/`memory.py`/`mcp.py` moved out to be siblings of `core/`, which now only holds the agent engine itself (`agent`, `config`, `session`, `codeloop`, `context_window`, `exception`). `clipboard.py` moved into `cli/` — it's only used by the interactive Textual chat
- 🎨 New `protocol/` module: `Message` moved out of `core/session.py` into `protocol/messages.py`; the JSON-RPC envelope builders (`notification`/`response`/`error_response`, error codes) `pycodeloop serve` was hand-assembling inline moved into `protocol/events.py`
- 🎨 `providers/generic.py` (one class doing config loading, three response-parsing strategies, a request-builder factory, and raw HTTP/SSE transport) split — the response parsers moved to a new `providers/_responses.py`, the config-driven request builder moved into `providers/_shapes.py` next to the message/tool-schema builders it already used. `GenericProvider` now only orchestrates config loading and HTTP transport
- 🎨 `Config._append_to_system_prompt` helper extracted (was duplicated between skills discovery and memory loading); `tools/__init__.py`'s `DEFAULT_TOOLS`/`READ_ONLY_TOOLS` no longer double-instantiate the tools they share
- 🗑️ Removed the `anthropic`/`openai` poetry extras — dead weight, `GenericProvider` is stdlib-only and never imports either SDK. The `mcp` extra (actually used, by `pycodeloop/mcp.py`) stays

**VS Code extension — now its own repo, [dotflow-io/vscodeloop](https://github.com/dotflow-io/vscodeloop)**

The extension moved out of this repo's `vscode-extension/` into its own, with full commit history preserved. It still ships as the `pycodeloop`/"CodeLoop" VS Code extension; only where the code lives changed.

- ⚙️ Provider gallery (⚙ → Select Provider…, or `/provider`): card picker for all 13 providers (Anthropic, OpenAI, Gemini, Grok, Groq, AWS Bedrock, Kimi, DeepSeek, Llama, Qwen, NVIDIA NIM, Ollama, LM Studio) with a connected/local/needs-key status per card, a per-provider model picker, and a custom-JSON/generic-URL fallback. API keys and the chosen model are remembered per provider, so switching back doesn't re-prompt
- ⚙️ Dedicated Sessions page (Sessions toolbar button, replacing the native quickpick): cards show message count, working directory, last-updated time, and an Active badge, each with a Switch action
- ⚙️ `pycodeloop.delegation` and `pycodeloop.memory` settings, gear-menu toggles, `/delegate` and `/memory` slash commands
- ⚙️ Claude Code-style status line ("● Thinking… · 12s") replacing the earlier 3-dot bubble — live elapsed-time counter, and switches to "N sub-agents working…" while parallel `delegate` calls are in flight
- ⚙️ Completed write_file/edit_file/delete_file tool cards now render the diff computed for the confirmation prompt (colored +/- lines, "Added N lines" summary) instead of discarding it for a bare "Edited path" string
- 🪲 A per-provider model choice that's since been retired by the vendor (e.g. Gemini's `gemini-2.5-flash`, no longer available to new API keys) used to keep 404ing every session until manually changed — the extension now self-heals it back to the provider's current default the next time it connects
- 🎨 Panel reworked to an owline-style visual language: thin 1px borders, sharp corners, monospace uppercase for buttons/labels, SVG line icons instead of emoji, no VS Code default rounded-button chrome — all still on `var(--vscode-*)` tokens so it follows the user's editor theme
- 🎨 "API Key" removed from the gear menu — redundant with the provider gallery's own connect/key flow, which is where the key actually gets set
- 🎨 `src/` restructured from a flat bag of `lib`/`config`/`webview` files into `features/` (chat, sessions, settings — each with its own controller), `vscode/` (webview shell, sidebar registration), `core-client/` (RPC client, process management, wire protocol), and `services/` (credentials, settings, storage, terminal, workspace)
- 🎨 `media/main.js` (1511 lines, one file) split into 9 plain `<script>` files (`dom`, `render-utils`, `chat-turns`, `chat-tools`, `chat-apikey`, `composer`, `menu`, `gallery`, `app`) loaded in a fixed order — still no bundler, they share one global scope by design, same as before
- 📘 ESLint added (flat config, `typescript-eslint`) with an `npm run lint` script
- 📘 `WebviewMessage` discriminated union replaces `onWebviewMessage(message: any)`; 11 near-identical gear-menu handlers deduplicated into one `onMenuClick(button, action)` helper
- 📘 `AGENTS.md` added at the (former) repo root capturing standing rules (provider JSONs synced across template dirs, verify model IDs against current vendor docs, no emoji icons, rebuild+reinstall the `.vsix` after every extension change) for skills discovery to pick up automatically

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
