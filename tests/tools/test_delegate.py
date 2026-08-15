"""Test DelegateTool"""

import threading
import unittest
from unittest import mock

from pycodeloop.abc.provider import Provider, ProviderResponse
from pycodeloop.tools import READ_ONLY_TOOLS
from pycodeloop.tools.delegate import DelegateTool


class FakeProvider(Provider):
    name = "fake"

    def __init__(self, scripted: list[ProviderResponse]) -> None:
        super().__init__(model="fake-model")
        self._scripted = list(scripted)
        self.requests: list[list] = []

    def complete(
        self, system_prompt, messages, tools, on_delta=None
    ) -> ProviderResponse:
        self.requests.append(tools)
        return self._scripted.pop(0)


class TestDelegateTool(unittest.TestCase):
    def test_returns_the_sub_agents_final_text(self):
        provider = FakeProvider([ProviderResponse(text="the answer is 42")])
        tool = DelegateTool(provider=provider, tools=list(READ_ONLY_TOOLS))

        result = tool.run(task="what is the answer?")

        self.assertFalse(result.is_error)
        self.assertEqual(result.output, "the answer is 42")

    def test_sub_agent_only_sees_the_tools_it_was_given(self):
        provider = FakeProvider([ProviderResponse(text="done")])
        tool = DelegateTool(provider=provider, tools=list(READ_ONLY_TOOLS))

        tool.run(task="investigate")

        sub_agent_tool_names = {t["name"] for t in provider.requests[0]}
        read_only_names = {t.name for t in READ_ONLY_TOOLS}
        self.assertEqual(sub_agent_tool_names, read_only_names)
        self.assertNotIn("write_file", sub_agent_tool_names)
        self.assertNotIn("bash", sub_agent_tool_names)
        self.assertNotIn("delegate", sub_agent_tool_names)

    def test_preview_shows_the_task(self):
        tool = DelegateTool(provider=FakeProvider([]), tools=[])

        self.assertEqual(
            tool.preview(task="investigate the bug"), "investigate the bug"
        )

    def test_wants_cancel_event_is_set(self):
        tool = DelegateTool(provider=FakeProvider([]), tools=[])

        self.assertTrue(tool.wants_cancel_event)

    def test_forwards_cancel_event_to_the_sub_agent(self):
        provider = FakeProvider([ProviderResponse(text="done")])
        tool = DelegateTool(provider=provider, tools=list(READ_ONLY_TOOLS))
        event = threading.Event()

        with mock.patch(
            "pycodeloop.core.agent.Agent.run", return_value="done"
        ) as run:
            tool.run(task="investigate", cancel_event=event)

        run.assert_called_once_with("investigate", cancel_event=event)

    def test_timeout_scales_with_max_turns_and_provider_timeout(self):
        class TimedProvider(FakeProvider):
            timeout = 30.0

        tool = DelegateTool(provider=TimedProvider([]), tools=[], max_turns=5)

        self.assertEqual(tool.timeout, 150.0)

    def test_timeout_falls_back_to_60s_when_provider_timeout_is_none(self):
        class NoTimeoutProvider(FakeProvider):
            timeout = None

        tool = DelegateTool(
            provider=NoTimeoutProvider([]), tools=[], max_turns=5
        )

        self.assertEqual(tool.timeout, 300.0)


if __name__ == "__main__":
    unittest.main()
