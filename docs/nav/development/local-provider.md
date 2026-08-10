# Local providers

`OpenAIProvider` accepts a `base_url` — point it at any server that speaks the OpenAI chat-completions API and it runs through the same code path as `api.openai.com`.

## Ollama

`OllamaProvider` (`pycodeloop.providers.OllamaProvider`) is `OpenAIProvider` pre-configured for a local Ollama server:

```python
from pycodeloop import Config
from pycodeloop.providers import OllamaProvider

config = Config(provider=OllamaProvider(model="llama3.1"))
```

Defaults: `base_url="http://localhost:11434/v1"`, `api_key="ollama"` (Ollama ignores it, the OpenAI client just requires a non-empty string).

From the CLI:

```bash
pycodeloop run "..." --provider ollama --model llama3.1
```

## Any other OpenAI-compatible server

LM Studio, vLLM, llama.cpp server, text-generation-webui, and similar all expose an OpenAI-compatible endpoint. Point `OpenAIProvider` at it directly:

```python
from pycodeloop.providers import OpenAIProvider

provider = OpenAIProvider(model="my-local-model", base_url="http://localhost:8000/v1", api_key="not-needed")
```

Or from the CLI with `--base-url`:

```bash
pycodeloop run "..." --provider openai --model my-local-model --base-url http://localhost:8000/v1
```

Tool-calling support depends on the server and the model — not every local model handles the tool-use protocol as reliably as Claude or GPT. If tool calls come back malformed, try a model explicitly documented as supporting function calling.
