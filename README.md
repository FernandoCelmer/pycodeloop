<p align="center">
  <img src="https://raw.githubusercontent.com/dotflow-io/pycodeloop/master/docs/assets/logo.png" alt="CodeLoop" width="120">
</p>
<p align="center">
  <strong>CodeLoop</strong>
</p>
<p align="center">
    <em>Provider-agnostic terminal coding agent — point it at a JSON file, not a vendor SDK.</em>
</p>
<p align="center">
<a href="https://pypi.org/project/pycodeloop/" target="_blank">
    <img src="https://img.shields.io/pypi/v/pycodeloop?style=flat-square" alt="PyPI">
</a>
<a href="https://pypi.org/project/pycodeloop/" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/pycodeloop?style=flat-square" alt="Python">
</a>
<a href="https://github.com/dotflow-io/pycodeloop/actions/workflows/test.yml" target="_blank">
    <img src="https://img.shields.io/github/actions/workflow/status/dotflow-io/pycodeloop/test.yml?label=tests&style=flat-square" alt="Tests">
</a>
<a href="https://github.com/dotflow-io/pycodeloop/blob/master/LICENSE" target="_blank">
    <img src="https://img.shields.io/github/license/dotflow-io/pycodeloop?style=flat-square" alt="License">
</a>
<a href="https://github.com/dotflow-io/pycodeloop" target="_blank">
    <img src="https://img.shields.io/github/stars/dotflow-io/pycodeloop?label=Stars&style=flat-square" alt="Stars">
</a>
</p>

---

**Documentation**: <a href="https://dotflow-io.github.io/pycodeloop/" target="_blank">https://dotflow-io.github.io/pycodeloop/</a>

**Source Code**: <a href="https://github.com/dotflow-io/pycodeloop" target="_blank">https://github.com/dotflow-io/pycodeloop</a>

---

CodeLoop is a terminal coding agent, in the shape of Claude Code, Codex, or Gemini CLI — except it isn't tied to any one of them. Point it at a plain JSON config and give it a prompt: it drives a tool-use loop (read, write, edit, grep, bash, git, web fetch) against your codebase until the task is done, streaming its reasoning to your shell the whole way.

The key features are:

* **Provider-agnostic**: Anthropic, OpenAI, Ollama, LM Studio, or any OpenAI-compatible endpoint — swapping models means swapping a JSON file, never touching code. `GenericProvider` talks HTTP directly, no vendor SDK required.
* **Fast to start**: one `pip install`, one JSON file, one prompt. No boilerplate, no framework to learn first.
* **Safe by default**: every write, edit, delete, shell command, commit, or HTTP call shows a diff or command preview and waits for your OK before running.
* **Full-screen chat**: bare `pycodeloop` drops you into a Textual-based terminal UI; `pycodeloop run` stays scriptable for CI and one-shot use.
* **Skills-aware**: auto-discovers `SKILL.md`/`CLAUDE.md`, `.cursorrules`, and `AGENTS.md` files already on disk and hands them to the agent.
* **MCP-ready**: connect any Model Context Protocol server over stdio with one flag; its tools show up alongside the built-in ones.
* **Sessions that persist**: conversations survive process restarts and can be resumed from a menu.
* **Also a library**: embed the same agent loop in your own app — see the [docs](https://dotflow-io.github.io/pycodeloop/) for the `Config`, `Agent`, and `Tool` APIs.
* **Editor integration**: a VS Code extension ([`vscode-extension/`](vscode-extension/)) puts the same agent in a sidebar panel.

## Requirements

Python 3.10+

## Installation

```bash
pip install pycodeloop
```

## Example

Set your key and point at a ready-made provider template:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pycodeloop run "list the files in this repo and summarize the project" \
  --provider templates/anthropic.json
```

Or drop into the full-screen chat instead of one-shot mode:

```bash
pycodeloop --provider templates/anthropic.json
```

Set it once as the default so you stop passing `--provider` every time:

```bash
export PYCODELOOP_PROVIDER=templates/anthropic.json
pycodeloop
```

### Switch providers

Every backend is the same JSON shape — [`templates/`](templates/) ships one per vendor:

```bash
pycodeloop run "..." --provider templates/anthropic.json   # Claude
pycodeloop run "..." --provider templates/openai.json      # GPT
pycodeloop run "..." --provider templates/ollama.json      # local, no key needed
pycodeloop run "..." --provider templates/lmstudio.json    # local, no key needed
```

Point it at any OpenAI-compatible HTTP endpoint by writing your own JSON — see [`docs/examples/provider.example.json`](docs/examples/provider.example.json) and the [JSON provider guide](docs/nav/development/json-provider.md). No Python required to add a new backend.

### More CLI flags

```bash
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

The CLI streams the model's text as it arrives, reports token usage after every turn, and caches discovered skills in `~/.pycodeloop/config.json` until something changes (`--skills-refresh` bypasses that).

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

This project is licensed under the terms of the MIT License.
