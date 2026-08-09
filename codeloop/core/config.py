"""Config module"""

from __future__ import annotations

from codeloop.abc.provider import Provider
from codeloop.abc.sessions import Sessions
from codeloop.abc.tool import Tool
from codeloop.core.agent import DEFAULT_SYSTEM_PROMPT
from codeloop.core.exception import NotProviderInstance
from codeloop.core.skills import (
    ReadSkillTool,
    discover_skills,
    render_skills_index,
)
from codeloop.core.tools import DEFAULT_TOOLS
from codeloop.providers import get_provider
from codeloop.settings import Settings


def _default_provider() -> Provider:
    return get_provider(
        Settings.PROVIDER, model=Settings.MODEL, api_key=Settings.API_KEY
    )


class Config:
    """
    Import:
        You can import the **Config** class with:

            from codeloop import Config

            from codeloop.providers import (
                AnthropicProvider,
                OpenAIProvider,
            )

    Example:
        `class` codeloop.core.config.Config

            config = Config(
                provider=AnthropicProvider(model="claude-sonnet-5"),
            )

    Args:
        provider (Optional[Provider]): LLM backend driving the agent.
            Defaults to the provider named by the `CODELOOP_PROVIDER`
            env var (anthropic when unset).

        tools (Optional[List[Tool]]): Tools exposed to the agent.
            Defaults to the built-in read/write/edit/grep/bash set.

        system_prompt (Optional[str]): Overrides the default system
            prompt.

        max_turns (int): Hard cap on tool-use loop iterations.

        max_history_turns (Optional[int]): Cap the session on the
            number of most recent user-initiated turns kept — older
            turns are dropped as a whole unit (never mid tool_calls/
            tool_result) before each provider call. Unset means the
            session grows without bound for the life of the process.

        skills (bool): Discover Claude Code skills/memory, Cursor rules,
            and AGENTS.md files on this machine and this project, expose
            them as a `read_skill` tool, and list them in the system
            prompt so the agent knows what's available.

        skill_sources (Optional[Set[str]]): Limit discovery to these
            sources ("claude-skill", "claude-memory", "cursor-rule",
            "agents-md"). Defaults to all of them.

        skills_refresh (bool): Skip the `~/.codeloop/config.json` skills
            cache and force a full rescan.

        storage (Optional[Sessions]): Persists the session so
            `CodeLoop.run(prompt, session_key=...)` can resume a
            conversation across process restarts. Unset means sessions
            stay in memory only, for the life of the `CodeLoop` instance.

    Attributes:
        provider (Provider):
        tools (List[Tool]):
        system_prompt (Optional[str]):
        max_turns (int):
        skills (List[Skill]):
        storage (Optional[Sessions]):
    """

    _PROVIDERS = {"provider": Provider, "storage": Sessions}

    def __init__(
        self,
        provider: Provider | None = None,
        tools: list[Tool] | None = None,
        system_prompt: str | None = None,
        max_turns: int = Settings.MAX_TURNS,
        max_history_turns: int | None = None,
        skills: bool = False,
        skill_sources: set[str] | None = None,
        skills_refresh: bool = False,
        storage: Sessions | None = None,
    ) -> None:
        self.provider = provider if provider is not None else _default_provider()
        self.tools = list(tools) if tools is not None else list(DEFAULT_TOOLS)
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.max_history_turns = max_history_turns
        self.skills = self._discover_skills(skills, skill_sources, skills_refresh)
        self.storage = storage

        self._validate()

    def _discover_skills(
        self, enabled: bool, sources: set[str] | None, refresh: bool
    ) -> list:
        if not enabled:
            return []

        found = discover_skills(sources=sources, use_cache=not refresh)

        if not found:
            return found

        self.tools = [*self.tools, ReadSkillTool(found)]
        base_prompt = (
            self.system_prompt
            if self.system_prompt is not None
            else DEFAULT_SYSTEM_PROMPT
        )
        self.system_prompt = f"{base_prompt}\n\n{render_skills_index(found)}"
        return found

    def _validate(self) -> None:
        for name, abc in self._PROVIDERS.items():
            value = getattr(self, name)

            if value is not None and not isinstance(value, abc):
                raise NotProviderInstance(name=name)
