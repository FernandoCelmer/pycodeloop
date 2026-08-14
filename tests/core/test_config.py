"""Test Config"""

import unittest

from pycodeloop.core.config import Config
from pycodeloop.providers import GenericProvider
from pycodeloop.tools._workspace import (
    is_workspace_enabled,
    set_workspace_enabled,
)


class TestConfigDelegation(unittest.TestCase):
    def _provider(self) -> GenericProvider:
        return GenericProvider(
            url="http://fake/v1/chat/completions", model="fake-model"
        )

    def test_delegation_off_by_default(self):
        config = Config(provider=self._provider(), storage=False)

        self.assertNotIn("delegate", [t.name for t in config.tools])

    def test_delegation_true_adds_the_delegate_tool(self):
        config = Config(
            provider=self._provider(), delegation=True, storage=False
        )

        self.assertIn("delegate", [t.name for t in config.tools])

    def test_delegate_tool_reuses_the_configs_provider(self):
        provider = self._provider()
        config = Config(provider=provider, delegation=True, storage=False)

        delegate = next(t for t in config.tools if t.name == "delegate")

        self.assertIs(delegate.provider, provider)


class TestConfigWorkspace(unittest.TestCase):
    def _provider(self) -> GenericProvider:
        return GenericProvider(
            url="http://fake/v1/chat/completions", model="fake-model"
        )

    def setUp(self):
        self.addCleanup(set_workspace_enabled, True)

    def test_workspace_on_by_default(self):
        Config(provider=self._provider(), storage=False)

        self.assertTrue(is_workspace_enabled())

    def test_workspace_false_disables_the_jail(self):
        Config(provider=self._provider(), storage=False, workspace=False)

        self.assertFalse(is_workspace_enabled())


if __name__ == "__main__":
    unittest.main()
