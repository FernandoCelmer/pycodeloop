# Custom providers

Any LLM backend can drive AIFlow — implement the `Provider` ABC (`aiflow.abc.provider.Provider`):

```python
from aiflow.abc.provider import Provider, ProviderResponse, ToolCall, Usage

class MyProvider(Provider):
    def complete(self, system_prompt, messages, tools, on_delta=None) -> ProviderResponse:
        response = my_api.chat(
            system=system_prompt,
            messages=messages,   # list[aiflow.core.session.Message]
            tools=tools,         # list[dict] JSON schema per tool
        )

        if on_delta is not None:
            for chunk in response.text_chunks():
                on_delta(chunk)

        return ProviderResponse(
            text=response.text,
            tool_calls=[
                ToolCall(id=call.id, name=call.name, arguments=call.arguments)
                for call in response.tool_calls
            ],
            stop_reason=response.finish_reason,
            usage=Usage(input_tokens=response.usage.input, output_tokens=response.usage.output),
        )
```

Streaming and usage tracking are both optional — return `ProviderResponse(text=..., tool_calls=...)` with defaults for everything else and it still works, just without live text and without token totals.

## Using it

Pass an instance directly:

```python
from aiflow import Config

config = Config(provider=MyProvider(model="my-model"))
```

Or load it dynamically by dotted path — useful for the CLI, which only takes strings:

```bash
aiflow run "..." --provider "my_package.my_module:MyProvider" --model my-model
```

`aiflow.providers.get_provider(name, **kwargs)` treats any name containing `:` as `module.path:ClassName`, imports the module, and instantiates the class with `**kwargs`. The CLI adds the current working directory to `sys.path` at startup, so a provider class in a plain `.py` file next to where you run `aiflow` is importable without installing anything.

## Validation

`Config` checks `isinstance(provider, Provider)` at construction time and raises `NotProviderInstance` if it isn't — a broken custom provider fails immediately, not three tool calls into a run.
