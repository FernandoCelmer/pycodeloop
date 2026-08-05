"""Config module"""

from __future__ import annotations

from aiflow.abc.provider import Provider
from aiflow.abc.tool import Tool
from aiflow.core.exception import NotProviderInstance
from aiflow.core.tools import DEFAULT_TOOLS
from aiflow.settings import Settings


def _default_provider() -> Provider:
    from aiflow.providers import get_provider

    return get_provider(Settings.PROVIDER, model=Settings.MODEL, api_key=Settings.API_KEY)


class Config:
    """
    Import:
        You can import the **Config** class with:

            from aiflow import Config

            from aiflow.providers import (
                AnthropicProvider,
                OpenAIProvider,
            )

    Example:
        `class` aiflow.core.config.Config

            config = Config(
                provider=AnthropicProvider(model="claude-sonnet-5"),
            )

    Args:
        provider (Optional[Provider]): LLM backend driving the agent.
            Defaults to the provider named by the `AIFLOW_PROVIDER`
            env var (anthropic when unset).

        tools (Optional[List[Tool]]): Tools exposed to the agent.
            Defaults to the built-in read/write/edit/grep/bash set.

        system_prompt (Optional[str]): Overrides the default system
            prompt.

        max_turns (int): Hard cap on tool-use loop iterations.

    Attributes:
        provider (Provider):
        tools (List[Tool]):
        system_prompt (Optional[str]):
        max_turns (int):
    """

    _PROVIDERS = {"provider": Provider}

    def __init__(
        self,
        provider: Provider | None = None,
        tools: list[Tool] | None = None,
        system_prompt: str | None = None,
        max_turns: int = Settings.MAX_TURNS,
    ) -> None:
        self.provider = provider if provider is not None else _default_provider()
        self.tools = tools if tools is not None else DEFAULT_TOOLS
        self.system_prompt = system_prompt
        self.max_turns = max_turns

        self._validate()

    def _validate(self) -> None:
        for name, abc in self._PROVIDERS.items():
            value = getattr(self, name)
            if value is not None and not isinstance(value, abc):
                raise NotProviderInstance(name=name)
