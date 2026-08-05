# Release Notes

## v0.1.0

Initial release.

- ⚙️ Core agent loop (`Agent`), dependency-injection container (`Config`), conversation state (`Session`), and the `AIFlow` entrypoint
- ⚙️ `Provider` ABC with built-in Anthropic, OpenAI, and Ollama implementations
- ⚙️ `Tool` ABC with built-in `read_file`, `write_file`, `edit_file`, `list_dir`, `grep`, `bash`
- ⚙️ Dangerous-tool confirmation gate with diff/command preview
- ⚙️ Streaming text output and per-turn/cumulative token usage tracking
- ⚙️ MCP client — connect to any Model Context Protocol server over stdio and use its tools like local ones
- ⚙️ Custom and local providers — dotted-path loading (`module.path:ClassName`) and `base_url` support for any OpenAI-compatible server
- ⚙️ `aiflow` CLI (`run`, `chat`) with permission prompts, streaming, and token usage reporting
