# Local providers

`GenericProvider` defaults to the OpenAI chat-completions request/response shape, so any server that speaks it — Ollama, LM Studio, vLLM, llama.cpp server, text-generation-webui, and similar — works by just pointing `url` at it.

## Ollama

[`templates/ollama.json`](https://github.com/dotflow-io/pycodeloop/blob/master/templates/ollama.json) is `GenericProvider` pre-configured for a local Ollama server:

```json
{
  "url": "http://localhost:11434/v1/chat/completions",
  "model": "llama3.1",
  "timeout": 120
}
```

```python
from pycodeloop import Config
from pycodeloop.providers import GenericProvider

config = Config(provider=GenericProvider.from_json("templates/ollama.json"))
```

No `api_key`/`api_key_env` — `GenericProvider` only sends an `Authorization` header when a key is actually present, so it's simply omitted (Ollama doesn't check one).

From the CLI:

```bash
pycodeloop run "..." --provider templates/ollama.json --model llama3.1
```

## Any other OpenAI-compatible server

LM Studio, vLLM, llama.cpp server, text-generation-webui, and similar all expose an OpenAI-compatible endpoint. [`templates/lmstudio.json`](https://github.com/dotflow-io/pycodeloop/blob/master/templates/lmstudio.json) is a ready-made example; point `url` at your own server the same way:

```python
from pycodeloop.providers import get_provider

provider = get_provider(
    "generic",
    url="http://localhost:8000/v1/chat/completions",
    model="my-local-model",
)
```

Or from the CLI with `--url`:

```bash
pycodeloop run "..." --provider generic --model my-local-model --url http://localhost:8000/v1/chat/completions
```

Tool-calling support depends on the server and the model — not every local model handles the tool-use protocol as reliably as Claude or GPT. If tool calls come back malformed, try a model explicitly documented as supporting function calling.
