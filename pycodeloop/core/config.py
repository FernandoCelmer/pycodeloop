"""Config module"""

from __future__ import annotations

from pycodeloop.abc.provider import Provider
from pycodeloop.abc.sessions import Sessions
from pycodeloop.abc.tool import Tool
from pycodeloop.core.agent import DEFAULT_SYSTEM_PROMPT
from pycodeloop.core.exception import NotProviderInstance
from pycodeloop.core.memory import RememberTool, load_memory, render_memory_prompt
from pycodeloop.core.store.sqlite_sessions import SqliteSessions
from pycodeloop.core.skills import (
    ReadSkillTool,
    discover_skills,
    render_skills_index,
)
from pycodeloop.core.tools import DEFAULT_TOOLS, READ_ONLY_TOOLS, DelegateTool
from pycodeloop.providers import get_provider
from pycodeloop.settings import Settings


def _default_provider() -> Provider:
    return get_provider(Settings.PROVIDER, model=Settings.MODEL)


def _default_storage() -> Sessions:
    return SqliteSessions()


class Config:
    """
    Import:
        You can import the **Config** class with:

            from pycodeloop import Config
            from pycodeloop.providers import GenericProvider

    Example:
        `class` pycodeloop.core.config.Config

            config = Config(
                provider=GenericProvider.from_json("path/to/config.json"),
            )

    Args:
        provider (Optional[Provider]): LLM backend driving the agent —
            always a `GenericProvider` under the hood. Defaults to the
            provider named by the `PYCODELOOP_PROVIDER` env var (a
            path to a JSON config file, a bare `"generic"` name, or a
            `'module.path:ClassName'`; a bundled Anthropic config when
            unset).

        tools (Optional[List[Tool]]): Tools exposed to the agent.
            Defaults to the built-in read/write/edit/grep/bash set.

        system_prompt (Optional[str]): Overrides the default system
            prompt.

        max_turns (int): Hard cap on tool-use loop iterations.

        max_history_turns (Optional[int]): Cap the session on the
            number of most recent user-initiated turns kept — older
            turns are dropped as a whole unit (never mid tool_calls/
            tool_result) before each provider call. Defaults to `20`;
            pass `None` to let the session grow without bound instead.

        skills (bool): Discover Claude Code skills/memory, Cursor rules,
            and AGENTS.md files on this machine and this project, expose
            them as a `read_skill` tool, and list them in the system
            prompt so the agent knows what's available.

        skill_sources (Optional[Set[str]]): Limit discovery to these
            sources ("claude-skill", "claude-memory", "cursor-rule",
            "agents-md"). Defaults to all of them.

        skills_refresh (bool): Skip the `~/.pycodeloop/config.json` skills
            cache and force a full rescan.

        delegation (bool): Expose a `delegate` tool that spawns a fresh
            sub-agent (same provider, read-only tools — no write/edit/
            delete/bash) for an independent subtask. Multiple `delegate`
            calls in one turn run in parallel, same as any other
            same-name, non-dangerous tool calls. Off by default.

        memory (bool): Load `.pycodeloop/memory.md` (if present) into the
            system prompt and expose a `remember` tool the agent uses to
            save standing corrections/preferences there — so a rule given
            in one session is still followed in the next, instead of the
            user repeating it every time. On by default.

        storage (Optional[Sessions]): Persists the session so
            `CodeLoop.run(prompt, session_key=...)` can resume a
            conversation across process restarts. Defaults to
            `SqliteSessions()` (`~/.pycodeloop/pycodeloop.db`). Pass `False`
            to keep sessions in memory only, for the life of the
            `CodeLoop` instance.

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
        max_history_turns: int | None = 20,
        skills: bool = False,
        skill_sources: set[str] | None = None,
        skills_refresh: bool = False,
        delegation: bool = False,
        memory: bool = True,
        storage: Sessions | bool | None = None,
    ) -> None:
        self.provider = provider if provider is not None else _default_provider()
        self.tools = list(tools) if tools is not None else list(DEFAULT_TOOLS)
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.max_history_turns = max_history_turns
        self.skills = self._discover_skills(skills, skill_sources, skills_refresh)
        if delegation:
            self.tools = [
                *self.tools,
                DelegateTool(provider=self.provider, tools=list(READ_ONLY_TOOLS)),
            ]
        if memory:
            self._load_memory()
        self.storage = None if storage is False else storage or _default_storage()

        self._validate()

    def _append_to_system_prompt(self, text: str) -> None:
        base_prompt = (
            self.system_prompt if self.system_prompt is not None else DEFAULT_SYSTEM_PROMPT
        )
        self.system_prompt = f"{base_prompt}\n\n{text}"

    def _discover_skills(
        self, enabled: bool, sources: set[str] | None, refresh: bool
    ) -> list:
        if not enabled:
            return []

        found = discover_skills(sources=sources, use_cache=not refresh)

        if not found:
            return found

        self.tools = [*self.tools, ReadSkillTool(found)]
        self._append_to_system_prompt(render_skills_index(found))
        return found

    def _load_memory(self) -> None:
        self.tools = [*self.tools, RememberTool()]

        content = load_memory()
        if not content:
            return

        self._append_to_system_prompt(render_memory_prompt(content))

    def _validate(self) -> None:
        for name, abc in self._PROVIDERS.items():
            value = getattr(self, name)

            if value is not None and not isinstance(value, abc):
                raise NotProviderInstance(name=name)
