# Permission prompts

Tools that change state — `write_file`, `edit_file`, `delete_file`, `bash`, `git_commit`, `http_request`, and every MCP tool — are marked `dangerous = True`. Give `Agent` a `confirm` callback and it gates every dangerous call behind it:

```python
from pycodeloop.core.agent import Agent

def confirm(name: str, preview: str) -> bool:
    print(preview)
    return input(f"run {name}? [y/N] ").lower() == "y"

agent = Agent(provider=provider, confirm=confirm)
```

`confirm` receives the tool name and a `preview` string — a unified diff for `write_file`/`edit_file`, the literal command line for `bash`, or `tool_name(arg=value, ...)` for MCP tools. It can return:

- `True` — run the tool.
- `False` — skip it; the model gets back `"User declined to run this tool."` and can adjust its plan.
- Any other non-empty string — skip it and feed that text back to the model as `"User declined and said: <text>"`, so you can redirect the agent instead of just blocking it.

No `confirm` callback set (the default) means dangerous tools just run — that's the library default so embedding CodeLoop in an automated pipeline doesn't require wiring a prompt.

## In the CLI

`pycodeloop run` and the TUI show a panel with the diff (or `$ command`) and ask a yes/no question before running anything dangerous, auto-confirming after 3 seconds of no response:

```bash
pycodeloop run "delete the old config file and rewrite main.py"
```

Pass `--yes` / `-y` to skip every confirmation — equivalent to not setting `confirm` at all:

```bash
pycodeloop run "..." --yes
```
