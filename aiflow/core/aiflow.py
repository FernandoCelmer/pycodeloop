"""AIFlow"""

from __future__ import annotations

from aiflow.core.agent import Agent
from aiflow.core.config import Config
from aiflow.core.session import Session


class AIFlow:
    """
    Import:
        You can import the **AIFlow** class directly from aiflow:

            from aiflow import AIFlow, Config
            from aiflow.providers import AnthropicProvider

    Example:
        `class` aiflow.core.aiflow.AIFlow

            config = Config(
                provider=AnthropicProvider(model="claude-sonnet-5")
            )

            flow = AIFlow(config=config)
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
            **agent_kwargs,
        )
        self.session = Session(system_prompt=self.agent.system_prompt)

    def run(self, prompt: str) -> str:
        """Run prompt to completion, keeping conversation history across calls."""
        return self.agent.run(prompt, session=self.session)
