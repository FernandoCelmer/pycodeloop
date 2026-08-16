<p align="center">
  <img src="https://raw.githubusercontent.com/dotflow-io/pycodeloop/master/docs/assets/logo.png" alt="CodeLoop" width="120">
</p>
<p align="center">
  <strong>CodeLoop</strong>
</p>
<p align="center">
    <em>Multi-provider coding agent — terminal or VS Code, point it at a JSON file, not a vendor SDK.</em>
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
<a href="https://marketplace.visualstudio.com/items?itemName=fernandocelmer.pycodeloop" target="_blank">
    <img src="https://img.shields.io/visual-studio-marketplace/v/fernandocelmer.pycodeloop?label=VS%20Marketplace&style=flat-square" alt="VS Marketplace">
</a>
</p>

---

**Documentation**: <a href="https://dotflow-io.github.io/pycodeloop/" target="_blank">https://dotflow-io.github.io/pycodeloop/</a>

**Source Code**: <a href="https://github.com/dotflow-io/pycodeloop" target="_blank">https://github.com/dotflow-io/pycodeloop</a>

---

CodeLoop is a terminal coding agent, in the shape of Claude Code, Codex, or Gemini CLI — except it isn't tied to any one of them. Point it at a plain JSON config and give it a prompt: it drives a tool-use loop (read, write, edit, grep, bash, git, web fetch) against your codebase until the task is done, streaming its reasoning to your shell the whole way.

The key features are:

* **Multi-provider**: Anthropic, OpenAI, Gemini, Grok (xAI), Groq, AWS Bedrock, Kimi (Moonshot AI), DeepSeek, Llama (Together AI), Qwen (Alibaba), NVIDIA NIM, Ollama, LM Studio, or any OpenAI-compatible endpoint — swapping models means swapping a JSON file, never touching code. `GenericProvider` talks HTTP directly, no vendor SDK required.
* **Fast to start**: one `pip install`, one JSON file, one prompt. No boilerplate, no framework to learn first.
* **Safe by default**: every write, edit, delete, shell command, commit, or HTTP call shows a diff or command preview and waits for your OK before running.
* **Full-screen chat**: bare `pycodeloop` drops you into a Textual-based terminal UI; `pycodeloop run` stays scriptable for CI and one-shot use.
* **Skills-aware**: auto-discovers `SKILL.md`/`CLAUDE.md`, `.cursorrules`, and `AGENTS.md` files already on disk and hands them to the agent.
* **MCP-ready**: connect any Model Context Protocol server over stdio with one flag; its tools show up alongside the built-in ones.
* **Sub-agent delegation** (`--delegate`, off by default): the agent can spawn read-only sub-agents for independent subtasks — several `delegate` calls in the same turn run in parallel, same as any other batch of safe tool calls.
* **Persistent memory** (`--memory`, on by default): corrections and standing preferences get saved to `.pycodeloop/memory.md` and loaded into every future session — say it once.
* **Sessions that persist**: conversations survive process restarts and can be resumed from a menu.
* **Also a library**: embed the same agent loop in your own app — see the [docs](https://dotflow-io.github.io/pycodeloop/) for the `Config`, `Agent`, and `Tool` APIs.
* **Editor integration**: a VS Code extension ([dotflow-io/vscodeloop](https://github.com/dotflow-io/vscodeloop), also on the [Marketplace](https://marketplace.visualstudio.com/items?itemName=fernandocelmer.pycodeloop)) puts the same agent in a sidebar panel.

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
pycodeloop run "..." --provider templates/gemini.json      # Gemini
pycodeloop run "..." --provider templates/grok.json        # Grok (xAI)
pycodeloop run "..." --provider templates/groq.json        # Groq (fast open-weight inference)
pycodeloop run "..." --provider templates/aws.json         # Amazon Bedrock (OpenAI-compatible)
pycodeloop run "..." --provider templates/kimi.json        # Kimi (Moonshot AI)
pycodeloop run "..." --provider templates/deepseek.json    # DeepSeek
pycodeloop run "..." --provider templates/llama.json       # Llama (Together AI)
pycodeloop run "..." --provider templates/qwen.json        # Qwen (Alibaba)
pycodeloop run "..." --provider templates/nvidia.json      # NVIDIA NIM
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

# Let the agent delegate independent subtasks to read-only sub-agents
pycodeloop run "..." --delegate

# Skip loading/saving .pycodeloop/memory.md for this run
pycodeloop run "..." --no-memory
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
| `sql_schema` | List a database's tables, or one table's columns |
| `sql_query` | Run a single read-only SQL statement (SELECT/WITH/EXPLAIN/PRAGMA/SHOW/DESCRIBE) |
| `delegate` | Spawn a read-only sub-agent for an independent subtask (`--delegate`, off by default) |
| `remember` | Save a standing correction/preference to `.pycodeloop/memory.md`, loaded into every future session's system prompt (`--memory`, on by default) |

`write_file`, `edit_file`, `delete_file`, `bash`, `git_commit`, `http_request`, and every MCP tool are marked dangerous and gated behind confirmation. `delegate` calls run in parallel with each other in the same turn — the underlying sub-agents only get read-only tools, so there's nothing to confirm.

`read_file` logs every read/write/edit/delete to `~/.pycodeloop/pycodeloop.db`, scoped to the session. Reading the exact same path/range twice with no change on disk in between returns a short notice instead of repeating the content, to save tokens — pass `force=true` to see it again.

When a tool fails, pycodeloop classifies the failure (rule-based, no LLM call) and injects a typed prefix ahead of the error so the agent can replan differently per kind — `[syntax_error]`, `[test_failure]`, `[runtime_exception]`, `[permission_denied]`, `[command_not_found]`, `[timeout]`, or `[unknown]`. The same `error_kind` is recorded in the JSONL execution trace.

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
