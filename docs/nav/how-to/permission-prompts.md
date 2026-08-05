# Permission prompts

Tools that change state — `write_file`, `edit_file`, `bash`, and every MCP tool — are marked `dangerous = True`. Give `Agent` a `confirm` callback and it gates every dangerous call behind it:

```python
from aiflow.core.agent import Agent

def confirm(name: str, preview: str) -> bool:
    print(preview)
    return input(f"run {name}? [y/N] ").lower() == "y"

agent = Agent(provider=provider, confirm=confirm)
```

`confirm` receives the tool name and a `preview` string — a unified diff for `write_file`/`edit_file`, the literal command line for `bash`, or `tool_name(arg=value, ...)` for MCP tools. Return `False` and the tool never runs; the model gets back `"User declined to run this tool."` instead of a result, and can adjust its plan.

No `confirm` callback set (the default) means dangerous tools just run — that's the library default so embedding AIFlow in an automated pipeline doesn't require wiring a prompt.

## In the CLI

`aiflow run` / `aiflow chat` show a colored panel (diff in green/red, `$ command` in yellow) and ask a yes/no question before running anything dangerous:

```bash
aiflow run "delete the old config file and rewrite main.py"
```

Pass `--yes` / `-y` to skip every confirmation — equivalent to not setting `confirm` at all:

```bash
aiflow run "..." --yes
```
