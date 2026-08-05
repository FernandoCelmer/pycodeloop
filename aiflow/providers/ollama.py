"""Ollama (local) provider."""

from __future__ import annotations

from aiflow.providers.openai import OpenAIProvider


class OllamaProvider(OpenAIProvider):
    """Talks to a local Ollama server through its OpenAI-compatible endpoint."""

    name = "ollama"

    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434/v1",
        api_key: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(model=model, api_key=api_key or "ollama", base_url=base_url, **kwargs)
