# CodeLoop for VS Code

Chat with [pycodeloop](https://github.com/dotflow-io/pycodeloop) — an
agentic coding assistant — from a sidebar view instead of the
terminal.

## How it works

The extension spawns `pycodeloop serve`, which speaks a small
JSON-RPC-2.0 protocol over its stdin/stdout (one JSON object per
line): text deltas, tool calls/results, usage, context %, retries,
compaction events, and a confirm request/response round-trip for
dangerous tools (write/edit/delete/bash). The webview renders all of
that and lets you approve or decline tool calls.

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
