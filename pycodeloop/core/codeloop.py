"""CodeLoop"""

from __future__ import annotations

import os
import threading

from pycodeloop.core.agent import Agent
from pycodeloop.core.config import Config
from pycodeloop.store.file_access_log import session_scope
from pycodeloop.store.usage_tracker import UsageTracker
from pycodeloop.core.session import Message, Session

_usage_tracker = UsageTracker()


class CodeLoop:
    """
    Import:
        You can import the **CodeLoop** class directly from pycodeloop:

            from pycodeloop import CodeLoop, Config
            from pycodeloop.providers import GenericProvider

    Example:
        `class` pycodeloop.core.codeloop.CodeLoop

            config = Config(
                provider=GenericProvider.from_json("path/to/config.json")
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

    def run(
        self,
        prompt: str,
        session_key: str | None = None,
        images: list[str] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> str:
        """Run prompt to completion, keeping history across calls.

        Pass `session_key` with a `Config(storage=...)` configured to
        resume a previous conversation: the session is loaded from
        storage before the run (falling back to the in-memory session
        on a cache miss) and saved back after.
        """
        can_persist = session_key is not None and self.config.storage is not None
        if can_persist:
            stored = self.config.storage.get(session_key)
            self.session = stored or Session(
                system_prompt=self.agent.system_prompt, cwd=os.getcwd()
            )
            self.agent.on_message = lambda: self.config.storage.post(
                session_key, self.session
            )
        else:
            self.agent.on_message = None

        usage_before = self.agent.usage
        with session_scope(session_key or "global"):
            result = self.agent.run(
                prompt, session=self.session, images=images, cancel_event=cancel_event
            )
        usage_after = self.agent.usage

        _usage_tracker.record_usage(
            session_key or "global",
            usage_after.input_tokens - usage_before.input_tokens,
            usage_after.output_tokens - usage_before.output_tokens,
        )

        if can_persist:
            self.config.storage.post(session_key, self.session)

        return result

    def ask(self, question: str) -> str:
        """One-shot Q&A against a read-only snapshot of the current
        session — doesn't touch `self.session`, run tools, or persist,
        so it's safe to call while `run()` is mid-turn on another thread."""
        messages = list(self.session.messages)
        last = messages[-1] if messages else None
        if last is not None and last.role == "assistant" and last.tool_calls:
            for call in last.tool_calls:
                messages.append(
                    Message(
                        role="tool",
                        tool_call_id=call["id"],
                        content="(pending — this tool hasn't finished yet)",
                    )
                )
        messages.append(Message(role="user", content=question))

        response = self.agent.provider.complete(
            system_prompt=self.agent.system_prompt,
            messages=messages,
            tools=[],
        )
        return response.text
