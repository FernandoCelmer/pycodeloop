"""Test usage.py"""

import tempfile
import unittest
from pathlib import Path

from pycodeloop.core.persistence.local_config import JsonFileStore
from pycodeloop.core.persistence.usage import UsageTracker


class TestUsage(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

        store = JsonFileStore(Path(self._tmpdir.name) / "config.json")
        self.tracker = UsageTracker(store=store)

    def test_get_usage_defaults_to_zero(self):
        self.assertEqual(
            self.tracker.get_usage("nope"),
            {"input_tokens": 0, "output_tokens": 0, "runs": 0},
        )

    def test_record_usage_accumulates(self):
        self.tracker.record_usage("s1", 100, 20)
        self.tracker.record_usage("s1", 50, 10)

        self.assertEqual(
            self.tracker.get_usage("s1"),
            {"input_tokens": 150, "output_tokens": 30, "runs": 2},
        )

    def test_record_usage_keeps_keys_independent(self):
        self.tracker.record_usage("s1", 100, 20)
        self.tracker.record_usage("s2", 5, 1)

        self.assertEqual(self.tracker.get_usage("s1")["input_tokens"], 100)
        self.assertEqual(self.tracker.get_usage("s2")["input_tokens"], 5)


if __name__ == "__main__":
    unittest.main()
