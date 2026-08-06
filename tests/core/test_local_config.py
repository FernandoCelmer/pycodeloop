"""Test local_config module"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import aiflow.core.local_config as local_config


class TestLocalConfig(unittest.TestCase):
    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        patcher = mock.patch.object(
            local_config, "CONFIG_PATH", Path(tmpdir.name) / "config.json"
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_read_returns_empty_dict_when_missing(self):
        self.assertEqual(local_config.read(), {})

    def test_set_and_get_section_round_trip(self):
        local_config.set_section("skills_cache", {"a": 1})

        self.assertEqual(local_config.get_section("skills_cache"), {"a": 1})

    def test_get_section_defaults_to_empty_dict(self):
        self.assertEqual(local_config.get_section("missing"), {})

    def test_set_section_preserves_other_sections(self):
        local_config.set_section("a", {"x": 1})
        local_config.set_section("b", {"y": 2})

        self.assertEqual(local_config.read(), {"a": {"x": 1}, "b": {"y": 2}})


if __name__ == "__main__":
    unittest.main()
