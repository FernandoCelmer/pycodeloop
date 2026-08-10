"""Providers __init__ module."""

import importlib

from pycodeloop.providers.anthropic import AnthropicProvider
from pycodeloop.providers.generic import GenericProvider
from pycodeloop.providers.ollama import OllamaProvider
from pycodeloop.providers.openai import OpenAIProvider

PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
    "generic": GenericProvider,
}

__all__ = [
    "AnthropicProvider",
    "GenericProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "get_provider",
    "PROVIDERS",
]


def get_provider(name: str, **kwargs):
    """Build a Provider by registry name (anthropic, openai, ollama,
    generic), by path to a JSON config file (see
    `pycodeloop.providers.generic`), or by dotted path
    'module.path:ClassName' for a custom Provider subclass."""
    if name.endswith(".json"):
        provider = GenericProvider.from_json(name)

        if kwargs.get("model"):
            provider.model = kwargs["model"]

        if kwargs.get("api_key"):
            provider.api_key = kwargs["api_key"]

        return provider

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
