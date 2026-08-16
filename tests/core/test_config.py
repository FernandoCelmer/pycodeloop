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


class TestConfigWorkspace(unittest.TestCase):
    def _provider(self) -> GenericProvider:
        return GenericProvider(
            url="http://fake/v1/chat/completions", model="fake-model"
        )

    def _read_file_tool(self, config: Config):
        return next(t for t in config.tools if t.name == "read_file")

    def test_workspace_on_by_default(self):
        config = Config(provider=self._provider(), storage=False)

        self.assertTrue(self._read_file_tool(config)._workspace)

    def test_workspace_false_disables_the_jail(self):
        config = Config(
            provider=self._provider(), storage=False, workspace=False
        )

        self.assertFalse(self._read_file_tool(config)._workspace)

    def test_two_configs_with_different_workspace_settings_dont_interfere(
        self,
    ):
        """Regression: workspace used to be a process-wide global — the
        Config built last would silently win for every Config's tools,
        not just its own."""
        jailed = Config(provider=self._provider(), storage=False)
        unjailed = Config(
            provider=self._provider(), storage=False, workspace=False
        )

        self.assertTrue(self._read_file_tool(jailed)._workspace)
        self.assertFalse(self._read_file_tool(unjailed)._workspace)


class TestConfigAutonomy(unittest.TestCase):
    def _provider(self) -> GenericProvider:
        return GenericProvider(
            url="http://fake/v1/chat/completions", model="fake-model"
        )

    def test_default_autonomy_is_safe_execute(self):
        config = Config(provider=self._provider(), storage=False)

        self.assertEqual(config.autonomy, "safe_execute")

    def test_autonomy_is_stored_normalized(self):
        config = Config(
            provider=self._provider(), storage=False, autonomy="manual"
        )

        self.assertEqual(config.autonomy, "manual")
        self.assertIsInstance(config.autonomy, str)

    def test_invalid_autonomy_raises(self):
        with self.assertRaises(ValueError):
            Config(
                provider=self._provider(),
                storage=False,
                autonomy="do_everything",
            )

    def test_delegate_tool_inherits_autonomy(self):
        config = Config(
            provider=self._provider(),
            storage=False,
            delegation=True,
            autonomy="full_project_loop",
        )

        delegate = next(t for t in config.tools if t.name == "delegate")

        self.assertEqual(delegate.autonomy, "full_project_loop")


if __name__ == "__main__":
    unittest.main()
