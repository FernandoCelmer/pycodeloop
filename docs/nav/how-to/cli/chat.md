# aiflow chat

Start an interactive session in the current directory. Same options as [`aiflow run`](run.md), conversation history kept across turns until you exit.

```bash
aiflow chat
```

```bash
aiflow chat --provider ollama --model llama3.1
```

Type `exit`, `quit`, or press `Ctrl+D` to leave.

The session behaves like a terminal coding agent: replies stream in as they're generated, dangerous tool calls (`write_file`, `edit_file`, `bash`, MCP tools) show a diff or command preview and ask for confirmation first, and token usage prints after every turn. See [Streaming](../streaming.md), [Permission prompts](../permission-prompts.md), and [Token usage](../token-usage.md).
