"""Test user_settings.py"""

import tempfile
import unittest
from pathlib import Path

from pycodeloop.core.persistence.local_config import JsonFileStore
from pycodeloop.core.persistence.user_settings import UserSettings


class TestUserSettings(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

        store = JsonFileStore(Path(self._tmpdir.name) / "config.json")
        self.settings = UserSettings(store=store)

    def test_get_settings_defaults_to_empty(self):
        self.assertEqual(self.settings.get_settings(), {})

    def test_set_setting_persists_it(self):
        self.settings.set_setting("provider", "openai")

        self.assertEqual(self.settings.get_settings(), {"provider": "openai"})

    def test_set_setting_does_not_clobber_other_keys(self):
        self.settings.set_setting("provider", "openai")
        self.settings.set_setting("model", "gpt-5")

        self.assertEqual(
            self.settings.get_settings(), {"provider": "openai", "model": "gpt-5"}
        )

    def test_clear_setting_removes_only_that_key(self):
        self.settings.set_setting("provider", "openai")
        self.settings.set_setting("model", "gpt-5")

        self.settings.clear_setting("provider")

        self.assertEqual(self.settings.get_settings(), {"model": "gpt-5"})


if __name__ == "__main__":
    unittest.main()
