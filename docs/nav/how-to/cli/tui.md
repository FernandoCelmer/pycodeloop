# aiflow tui

Start the full-screen [Textual](https://textual.textualize.io/) interface. This is what bare `aiflow` runs — `tui` is the explicit form when you want to pass options without triggering a subcommand parse ambiguity.

```bash
aiflow
# same as
aiflow tui
```

Textual owns the whole terminal, so there's no readline/redraw contention — text streams in live, and the prompt at the bottom is never blocked: messages typed while the agent is still working queue up and run in order once it's free.

Same options as [`aiflow run`](run.md):

```bash
aiflow tui --provider openai --model gpt-5
aiflow tui --mcp "npx -y @modelcontextprotocol/server-filesystem ." --yes
```

Dangerous tool calls (`write_file`, `edit_file`, `delete_file`, `bash`, MCP tools) show a diff or command preview inline and wait for a y/n answer typed into the same input box — answering doesn't require leaving the prompt. `Ctrl+C` quits.
