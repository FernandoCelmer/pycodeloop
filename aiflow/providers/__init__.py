"""Providers __init__ module."""

import importlib

from aiflow.providers.anthropic import AnthropicProvider
from aiflow.providers.ollama import OllamaProvider
from aiflow.providers.openai import OpenAIProvider

PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}

__all__ = ["AnthropicProvider", "OllamaProvider", "OpenAIProvider", "get_provider", "PROVIDERS"]


def get_provider(name: str, **kwargs):
    """Build a Provider by registry name (anthropic, openai, ollama) or by
    dotted path 'module.path:ClassName' for a custom Provider subclass."""
    if ":" in name:
        module_path, class_name = name.split(":", 1)
        module = importlib.import_module(module_path)
        provider_cls = getattr(module, class_name)
        return provider_cls(**kwargs)

    try:
        provider_cls = PROVIDERS[name]
    except KeyError:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {list(PROVIDERS)}, "
            "or 'module.path:ClassName' for a custom Provider."
        ) from None
    return provider_cls(**kwargs)
