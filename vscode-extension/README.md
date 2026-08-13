# CodeLoop for VS Code

Chat with [pycodeloop](https://github.com/dotflow-io/pycodeloop) — an
agentic coding assistant — from a sidebar view instead of the
terminal.

## Features

- **Sidebar chat** — CodeLoop lives in the activity bar, no terminal split needed.
- **Streamed replies** rendered as markdown: headings, lists, links, inline/fenced code, bold/italic.
- **Tool call cards** — every `read_file`/`edit_file`/`bash`/etc. call shows up as a collapsible card (icon, name, args preview, status); click to expand args and result.
- **Approve or decline dangerous tools** — `write_file`, `edit_file`, `delete_file`, `bash`, `git_commit`, `http_request`, and MCP tools each pause for confirmation with a diff/command preview, unless auto-approve is on.
- **Multiple sessions** — start a new one (`CodeLoop: New Session`) or switch between existing ones (`CodeLoop: Switch Session…`), each keeping its own history.
- **Image attachments** — paste a screenshot straight into the prompt box, or attach one from disk, to give the agent visual context.
- **Live token usage and context %** — see input/output tokens per turn and how full the context window is, with compaction events surfaced inline.
- **Skills-aware** — auto-discovers Claude Code, Cursor, and `AGENTS.md` skills already on disk, no setup required.

## How it works

The extension spawns `pycodeloop serve`, which speaks a small
JSON-RPC-2.0 protocol over its stdin/stdout (one JSON object per
line): text deltas, tool calls/results, usage, context %, retries,
compaction events, and a confirm request/response round-trip for
dangerous tools.

## Requirements

- `pycodeloop` installed and on `PATH` (or set `pycodeloop.command` to
  its full path).
- A provider configured the same way as the CLI — see the main
  project's README for `templates/*.json` and the `pycodeloop.provider`
  / `pycodeloop.model` / `pycodeloop.url` settings below.

## Settings

| Setting | Description |
|---|---|
| `pycodeloop.command` | Path to the `pycodeloop` executable. Default `pycodeloop`. |
| `pycodeloop.provider` | JSON config path, `generic`, or `module:Class`. Empty uses pycodeloop's default. |
| `pycodeloop.model` | Model override. |
| `pycodeloop.url` | Endpoint URL, required when `pycodeloop.provider` is `generic`. |
| `pycodeloop.skills` | Discover Claude/Cursor/AGENTS.md skills. Default `true`. |

## Development

```bash
npm install
npm run compile   # or `npm run watch`
```

Press F5 in VS Code (with this folder open) to launch an Extension
Development Host.
