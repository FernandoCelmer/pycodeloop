"""CodeLoop"""

from __future__ import annotations

import os

from pycodeloop.core.agent import Agent
from pycodeloop.core.config import Config
from pycodeloop.core.persistence.usage import UsageTracker
from pycodeloop.core.session import Session

_usage_tracker = UsageTracker()


class CodeLoop:
    """
    Import:
        You can import the **CodeLoop** class directly from pycodeloop:

            from pycodeloop import CodeLoop, Config
            from pycodeloop.providers import AnthropicProvider

    Example:
        `class` pycodeloop.core.codeloop.CodeLoop

            config = Config(
                provider=AnthropicProvider(model="claude-sonnet-5")
            )

            flow = CodeLoop(config=config)
            flow.run("list the files in this repo and summarize the project")

    Args:
        config (Optional[Config]): Configuration class.

    Attributes:
        config (Config):

        agent (Agent):

        session (Session): Conversation history, kept across `run()` calls
            so the agent remembers earlier turns.
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config if config else Config()

        agent_kwargs = {}
        if self.config.system_prompt is not None:
            agent_kwargs["system_prompt"] = self.config.system_prompt

        self.agent = Agent(
            provider=self.config.provider,
            tools=self.config.tools,
            max_turns=self.config.max_turns,
            max_history_turns=self.config.max_history_turns,
            **agent_kwargs,
        )

        self.session = Session(system_prompt=self.agent.system_prompt, cwd=os.getcwd())

    def run(self, prompt: str, session_key: str | None = None) -> str:
        """Run prompt to completion, keeping history across calls.

        Pass `session_key` with a `Config(storage=...)` configured to
        resume a previous conversation: the session is loaded from
        storage before the run (falling back to the in-memory session
        on a cache miss) and saved back after.
        """
        if session_key is not None and self.config.storage is not None:
            stored = self.config.storage.get(session_key)
            if stored is not None:
                self.session = stored

        usage_before = self.agent.usage
        result = self.agent.run(prompt, session=self.session)
        usage_after = self.agent.usage

        _usage_tracker.record_usage(
            session_key or "global",
            usage_after.input_tokens - usage_before.input_tokens,
            usage_after.output_tokens - usage_before.output_tokens,
        )

        if session_key is not None and self.config.storage is not None:
            self.config.storage.post(session_key, self.session)

        return result
