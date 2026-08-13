<div align="center">

**Bring your own model. Swap providers. Ship an agent.**

[![PyPI](https://img.shields.io/pypi/v/pycodeloop?style=flat-square)](https://pypi.org/project/pycodeloop/)
[![Python](https://img.shields.io/pypi/pyversions/pycodeloop?style=flat-square)](https://pypi.org/project/pycodeloop/)
[![Stars](https://img.shields.io/github/stars/dotflow-io/pycodeloop?label=Stars&style=flat-square)](https://github.com/dotflow-io/pycodeloop)

</div>

---

# CodeLoop

CodeLoop is a terminal coding agent — in the shape of Claude Code, Codex, or Gemini CLI. Point it at a provider (a plain JSON config, no code) and give it a prompt: it drives a tool-use loop (read, write, edit, grep, bash, git, web fetch) until the task is done, right from your shell.

## Why CodeLoop?

- **Any model, one JSON file** — Anthropic, OpenAI, Ollama, LM Studio, or any OpenAI-compatible endpoint. No vendor SDKs, no code changes to switch — `GenericProvider` speaks HTTP directly.
- **Full-screen chat** — bare `pycodeloop` drops you into a Textual-based interface.
- **Asks before doing anything risky** — write/edit/delete/bash/commit/HTTP calls show a diff or command preview and wait for your OK, unless you pass `--yes`.
- **Skills-aware** — auto-discovers `SKILL.md`/`CLAUDE.md`, `.cursorrules`, and `AGENTS.md` files already on disk.
- **Sessions that persist** — conversations survive process restarts; switch between saved sessions.
- **VS Code extension** — chat with CodeLoop from a sidebar panel instead of the terminal ([`vscode-extension/`](vscode-extension/)).

## Install

```bash
pip install pycodeloop
```

## Quick Start

Pick a provider template and set your key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pycodeloop run "list the files in this repo and summarize the project" \
  --provider templates/anthropic.json
```

Or drop into the full-screen chat:

```bash
pycodeloop --provider templates/anthropic.json
```

Set it once as the default instead of passing `--provider` every time:

```bash
export PYCODELOOP_PROVIDER=templates/anthropic.json
pycodeloop
```

## Providers

Every backend is the same JSON shape fed to `GenericProvider` — swapping models means swapping a file, nothing else. Ready-made templates live in [`templates/`](templates/):

```bash
pycodeloop run "..." --provider templates/anthropic.json   # Claude
pycodeloop run "..." --provider templates/openai.json      # GPT
pycodeloop run "..." --provider templates/ollama.json      # local, no key needed
pycodeloop run "..." --provider templates/lmstudio.json    # local, no key needed
```

Point it at any OpenAI-compatible HTTP endpoint by writing your own JSON — see [`docs/examples/provider.example.json`](docs/examples/provider.example.json) and the [JSON provider guide](docs/nav/development/json-provider.md). No Python required to add a new backend.

## CLI

```bash
# Bare pycodeloop drops into the full-screen chat
pycodeloop

# One-shot, non-interactive (scripting/CI)
pycodeloop run "add a docstring to pycodeloop/core/agent.py"

# Override provider/model per invocation
pycodeloop run "..." --provider templates/openai.json --model gpt-5

# Skip confirmation prompts for dangerous tools
pycodeloop run "..." --yes

# Connect an MCP server, one flag per server
pycodeloop run "list every allowed directory" \
  --mcp "npx -y @modelcontextprotocol/server-filesystem ."

# Skip skills auto-discovery
pycodeloop run "..." --no-skills
```

The CLI behaves like a terminal coding agent:

- **Streams** the model's text as it arrives instead of waiting for the full reply.
- **Asks before running** `write_file`, `edit_file`, `delete_file`, `bash`, `git_commit`, `http_request`, or any MCP tool — shows a diff (or the shell command) and waits for confirmation, auto-running after 3s of no response. `--yes` skips this.
- **Reports token usage** after every turn: input/output tokens for that turn plus the running session total.
- **Discovers skills automatically** — `SKILL.md`/`CLAUDE.md` (Claude Code), `.mdc`/`.cursorrules` (Cursor), and `AGENTS.md` files already on disk are indexed and exposed to the agent via a `read_skill` tool, cached in `~/.pycodeloop/config.json` until something changes. `--no-skills` turns this off; `--skills-refresh` bypasses the cache.

## Tools

Ships with the actions an agent needs to actually change code:

| Tool | Purpose |
|------|---------|
| `read_file` | Read a file, optionally a line range |
| `write_file` | Create or overwrite a file |
| `edit_file` | Replace an exact substring in a file |
| `delete_file` | Delete a file |
| `list_dir` | List a directory |
| `glob` | Find files matching a glob pattern |
| `grep` | Regex search across files |
| `bash` | Run a shell command with a timeout |
| `web_fetch` | Fetch a URL and extract its text |
| `http_request` | Call a JSON HTTP API — any method, headers, body |
| `git_status` | Show the working tree status |
| `git_diff` | Show unstaged or staged changes |
| `git_log` | Show recent commit history |
| `git_commit` | Stage and commit changes |
| `env` | Read environment variables (secrets masked) |
| `todo` | Track a checklist across turns in a session |

`write_file`, `edit_file`, `delete_file`, `bash`, `git_commit`, `http_request`, and every MCP tool are marked dangerous and gated behind confirmation.

## MCP servers

Connect to any Model Context Protocol server over stdio and its tools show up alongside the built-in ones — no config beyond a flag:

```bash
pycodeloop run "list every allowed directory" \
  --mcp "npx -y @modelcontextprotocol/server-filesystem ."
```

## Sessions

Conversations persist to `~/.pycodeloop/sessions/` and survive process restarts. In the full-screen chat, switch between saved sessions from the menu.

## Using it as a library

CodeLoop is also a small Python library if you want to embed the agent loop in your own app — see [`docs/`](docs/) for the `Config`, `Agent`, and `Tool` APIs.

## Commit Style

| Icon | Type      | Description                                |
|------|-----------|--------------------------------------------|
| ⚙️   | FEATURE   | New feature                                |
| 📝   | PEP8      | Formatting fixes following PEP8            |
| 📌   | ISSUE     | Reference to issue                         |
| 🪲   | BUG       | Bug fix                                    |
| 📘   | DOCS      | Documentation changes                      |
| 📦   | PyPI      | PyPI releases                              |
| ❤️️   | TEST      | Automated tests                            |
| ⬆️   | CI/CD     | Changes in continuous integration/delivery |
| ⚠️   | SECURITY  | Security improvements                      |

## License

![GitHub License](https://img.shields.io/github/license/dotflow-io/pycodeloop)

This project is licensed under the terms of the MIT License.
