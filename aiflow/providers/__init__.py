"""Providers __init__ module."""

from aiflow.providers.anthropic import AnthropicProvider
from aiflow.providers.openai import OpenAIProvider

PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}

__all__ = ["AnthropicProvider", "OpenAIProvider", "get_provider", "PROVIDERS"]


def get_provider(name: str, **kwargs):
    try:
        provider_cls = PROVIDERS[name]
    except KeyError:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {list(PROVIDERS)}"
        ) from None
    return provider_cls(**kwargs)
