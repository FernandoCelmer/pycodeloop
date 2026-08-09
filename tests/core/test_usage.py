"""Test usage.py"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from codeloop.core import local_config
from codeloop.core.usage import get_usage, record_usage


class TestUsage(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

        patcher = mock.patch.object(
            local_config, "CONFIG_PATH", Path(self._tmpdir.name) / "config.json"
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_get_usage_defaults_to_zero(self):
        self.assertEqual(
            get_usage("nope"), {"input_tokens": 0, "output_tokens": 0, "runs": 0}
        )

    def test_record_usage_accumulates(self):
        record_usage("s1", 100, 20)
        record_usage("s1", 50, 10)

        self.assertEqual(
            get_usage("s1"), {"input_tokens": 150, "output_tokens": 30, "runs": 2}
        )

    def test_record_usage_keeps_keys_independent(self):
        record_usage("s1", 100, 20)
        record_usage("s2", 5, 1)

        self.assertEqual(get_usage("s1")["input_tokens"], 100)
        self.assertEqual(get_usage("s2")["input_tokens"], 5)


if __name__ == "__main__":
    unittest.main()
