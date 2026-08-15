"""Test EnvTool"""

import unittest
from unittest import mock

from pycodeloop.tools.env import EnvTool


class TestEnvTool(unittest.TestCase):
    def test_reads_single_var(self):
        with mock.patch.dict("os.environ", {"MY_VAR": "hello"}):
            result = EnvTool().run(name="MY_VAR")

        self.assertEqual(result.output, "MY_VAR=hello")

    def test_masks_sensitive_var(self):
        with mock.patch.dict("os.environ", {"MY_API_KEY": "sk-secret"}):
            result = EnvTool().run(name="MY_API_KEY")

        self.assertEqual(result.output, "MY_API_KEY=***")

    def test_masks_a_credential_embedded_in_a_url_value(self):
        with mock.patch.dict(
            "os.environ",
            {"DATABASE_URL": "postgres://user:hunter2@db.internal/app"},
        ):
            result = EnvTool().run(name="DATABASE_URL")

        self.assertEqual(result.output, "DATABASE_URL=***")

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

    def test_masks_pass_variants_and_auth(self):
        env = {
            "MY_PASS": "secret",
            "DB_PASSWD": "x",
            "AUTH": "bearer xxx",
            "SESSION_ID": "abc",
            "HOME": "/tmp",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            result = EnvTool().run()

        self.assertIn("MY_PASS=***", result.output)
        self.assertIn("DB_PASSWD=***", result.output)
        self.assertIn("AUTH=***", result.output)
        self.assertIn("SESSION_ID=***", result.output)
        self.assertIn("HOME=/tmp", result.output)

    def test_is_dangerous_and_requires_confirmation(self):
        self.assertTrue(EnvTool().dangerous)

    def test_preview_names_the_single_variable_being_read(self):
        self.assertEqual(
            EnvTool().preview(name="MY_API_KEY"), "$ env MY_API_KEY"
        )

    def test_preview_warns_about_listing_every_variable(self):
        preview = EnvTool().preview()

        self.assertIn("all variable names and masked values", preview)


if __name__ == "__main__":
    unittest.main()
