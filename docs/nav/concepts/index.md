# Concepts

CodeLoop has four moving pieces:

```
Config(provider, tools) → CodeLoop → Agent → loop(Provider ↔ Tools) → Session
```

- **[Agent loop](concept-agent-loop.md)** — the tool-use loop that drives a conversation until the model stops calling tools.
- **[Providers](concept-providers.md)** — the LLM backend abstraction. Anthropic and OpenAI ship built-in; anything else implements the same interface.
- **[Tools](concept-tools.md)** — the actions the agent can take: read/write/edit files, grep, run shell commands, or call an MCP server.
- **[Config](concept-config.md)** — the dependency-injection container that wires a provider and a tool set together.
