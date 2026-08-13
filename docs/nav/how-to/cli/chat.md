# pycodeloop chat

Start the full-screen [Textual](https://textual.textualize.io/) interface. This is what bare `pycodeloop` runs — `chat` is the explicit form when you want to pass options without triggering a subcommand parse ambiguity.

```bash
pycodeloop
# same as
pycodeloop chat
```

Textual owns the whole terminal, so there's no readline/redraw contention — text streams in live, and the prompt at the bottom is never blocked: messages typed while the agent is still working queue up and run in order once it's free.

Same options as [`pycodeloop run`](run.md):

```bash
pycodeloop chat --provider templates/openai.json --model gpt-5
pycodeloop chat --mcp "npx -y @modelcontextprotocol/server-filesystem ." --yes
```

Dangerous tool calls (`write_file`, `edit_file`, `delete_file`, `bash`, MCP tools) show a diff or command preview inline and wait for a y/n answer typed into the same input box — answering doesn't require leaving the prompt. `Ctrl+C` quits.
