# Release Notes

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
