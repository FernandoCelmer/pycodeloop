"""Test local_config module"""

import tempfile
import unittest
from pathlib import Path

from codeloop.core.persistence.local_config import JsonFileStore


class TestJsonFileStore(unittest.TestCase):
    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.store = JsonFileStore(Path(tmpdir.name) / "config.json")

    def test_read_returns_empty_dict_when_missing(self):
        self.assertEqual(self.store.read(), {})

    def test_set_and_get_section_round_trip(self):
        self.store.set_section("skills", {"a": 1})

        self.assertEqual(self.store.get_section("skills"), {"a": 1})

    def test_get_section_defaults_to_empty_dict(self):
        self.assertEqual(self.store.get_section("missing"), {})

    def test_set_section_preserves_other_sections(self):
        self.store.set_section("a", {"x": 1})
        self.store.set_section("b", {"y": 2})

        self.assertEqual(self.store.read(), {"a": {"x": 1}, "b": {"y": 2}})


if __name__ == "__main__":
    unittest.main()
