"""Test Config"""

import unittest

from pycodeloop.core.config import Config
from pycodeloop.providers import GenericProvider


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


if __name__ == "__main__":
    unittest.main()
