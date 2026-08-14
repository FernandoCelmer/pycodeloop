# Custom tools

Subclass `Tool` (`pycodeloop.abc.tool.Tool`):

```python
from pycodeloop.abc.tool import Tool, ToolResult

class MyTool(Tool):
    name = "my_tool"
    description = "Does a thing."
    parameters = {
        "type": "object",
        "properties": {"x": {"type": "string"}},
        "required": ["x"],
    }

    def run(self, x: str) -> ToolResult:
        return ToolResult(output=f"did {x}")
```

`parameters` is a JSON schema — it's sent to the provider verbatim so the model knows what arguments to pass.

## Making it dangerous

If the tool changes state, set `dangerous = True` and override `preview()` to summarize what will happen before it happens:

```python
class DeployTool(Tool):
    name = "deploy"
    description = "Deploys the current branch to production."
    dangerous = True

    def preview(self, **kwargs) -> str:
        return f"Deploy branch {kwargs.get('branch', 'main')} to production"

    def run(self, branch: str = "main") -> ToolResult:
        ...
        return ToolResult(output=f"Deployed {branch}")
```

See [Permission prompts](permission-prompts.md) for how `preview()` and the `confirm` hook interact.

## Wiring it in

```python
from pycodeloop import Config
from pycodeloop.tools import DEFAULT_TOOLS

config = Config(tools=DEFAULT_TOOLS + [MyTool()])
```

Or replace the built-in set entirely by passing only your own tools.
