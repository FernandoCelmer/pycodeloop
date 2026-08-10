"""Test EnvTool"""

import unittest
from unittest import mock

from pycodeloop.core.tools.env import EnvTool


class TestEnvTool(unittest.TestCase):
    def test_reads_single_var(self):
        with mock.patch.dict("os.environ", {"MY_VAR": "hello"}):
            result = EnvTool().run(name="MY_VAR")

        self.assertEqual(result.output, "MY_VAR=hello")

    def test_masks_sensitive_var(self):
        with mock.patch.dict("os.environ", {"MY_API_KEY": "sk-secret"}):
            result = EnvTool().run(name="MY_API_KEY")

        self.assertEqual(result.output, "MY_API_KEY=***")

    def test_reports_missing_var(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            result = EnvTool().run(name="NOPE")

        self.assertTrue(result.is_error)

    def test_lists_all_vars_masked(self):
        with mock.patch.dict(
            "os.environ", {"PLAIN": "1", "SECRET_TOKEN": "shh"}, clear=True
        ):
            result = EnvTool().run()

        self.assertIn("PLAIN=1", result.output)
        self.assertIn("SECRET_TOKEN=***", result.output)
        self.assertNotIn("shh", result.output)


if __name__ == "__main__":
    unittest.main()
