"""Test flow.py's build_flow error paths and JSON-provider dispatch"""

import unittest
from unittest import mock

import typer

from aiflow.cli.flow import build_flow
from aiflow.providers.generic import GenericProvider


class TestBuildFlowGenericProvider(unittest.TestCase):
    def test_generic_provider_without_url_exits(self):
        with self.assertRaises(typer.Exit):
            build_flow(provider_name="generic", model="m", url=None)

    def test_generic_provider_with_url_builds(self):
        flow, name, model = build_flow(
            provider_name="generic",
            model="my-model",
            url="http://fake/v1/chat/completions",
        )

        self.assertIsInstance(flow.agent.provider, GenericProvider)
        self.assertEqual(flow.agent.provider.url, "http://fake/v1/chat/completions")
        self.assertEqual(name, "generic")
        self.assertEqual(model, "my-model")


class TestBuildFlowJsonProvider(unittest.TestCase):
    def test_json_config_path_builds_generic_provider(self):
        flow, name, _model = build_flow(
            provider_name="templates/anthropic.json",
            model="explicit-model",
        )

        self.assertIsInstance(flow.agent.provider, GenericProvider)
        self.assertEqual(flow.agent.provider.model, "explicit-model")
        self.assertEqual(name, "templates/anthropic.json")


class TestBuildFlowCallbackWiring(unittest.TestCase):
    def test_agent_callbacks_are_all_wired(self):
        flow, _name, _model = build_flow(
            provider_name="generic",
            model="my-model",
            url="http://fake/v1/chat/completions",
        )

        self.assertIsNotNone(flow.agent.on_request)
        self.assertIsNotNone(flow.agent.on_tool_call)
        self.assertIsNotNone(flow.agent.on_tool_result)
        self.assertIsNotNone(flow.agent.on_text_delta)
        self.assertIsNotNone(flow.agent.on_usage)
        self.assertIsNotNone(flow.agent.confirm)

    def test_confirm_auto_approves_when_yes_flag_set(self):
        flow, _name, _model = build_flow(
            provider_name="generic",
            model="my-model",
            url="http://fake/v1/chat/completions",
            auto_approve=True,
        )

        self.assertTrue(flow.agent.confirm("bash", "$ echo hi"))

    def test_confirm_times_out_and_auto_confirms(self):
        flow, _name, _model = build_flow(
            provider_name="generic",
            model="my-model",
            url="http://fake/v1/chat/completions",
        )

        with mock.patch("aiflow.cli.flow._CONFIRM_TIMEOUT", 0.05):
            # No stdin input is available in a test process, so the
            # background reader thread just blocks on input() forever
            # and this must time out and auto-confirm rather than hang.
            result = flow.agent.confirm("bash", "$ echo hi")

        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
