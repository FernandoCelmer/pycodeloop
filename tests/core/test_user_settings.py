"""Test user_settings.py"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from codeloop.core import local_config
from codeloop.core.user_settings import clear_setting, get_settings, set_setting


class TestUserSettings(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

        patcher = mock.patch.object(
            local_config, "CONFIG_PATH", Path(self._tmpdir.name) / "config.json"
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_get_settings_defaults_to_empty(self):
        self.assertEqual(get_settings(), {})

    def test_set_setting_persists_it(self):
        set_setting("provider", "openai")

        self.assertEqual(get_settings(), {"provider": "openai"})

    def test_set_setting_does_not_clobber_other_keys(self):
        set_setting("provider", "openai")
        set_setting("model", "gpt-5")

        self.assertEqual(get_settings(), {"provider": "openai", "model": "gpt-5"})

    def test_clear_setting_removes_only_that_key(self):
        set_setting("provider", "openai")
        set_setting("model", "gpt-5")

        clear_setting("provider")

        self.assertEqual(get_settings(), {"model": "gpt-5"})


if __name__ == "__main__":
    unittest.main()
