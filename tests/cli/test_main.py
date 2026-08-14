"""Test the --version flag"""

import unittest

from typer.testing import CliRunner

from pycodeloop import __version__
from pycodeloop.cli.main import app


class TestVersionFlag(unittest.TestCase):
    def test_prints_the_installed_version_and_exits(self):
        result = CliRunner().invoke(app, ["--version"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn(__version__, result.stdout)

    def test_short_flag_works_too(self):
        result = CliRunner().invoke(app, ["-V"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn(__version__, result.stdout)


if __name__ == "__main__":
    unittest.main()
