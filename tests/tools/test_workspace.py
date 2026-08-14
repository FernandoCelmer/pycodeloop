"""Test workspace path jail and URL scheme guards."""

import os
import tempfile
import unittest
from pathlib import Path

from pycodeloop.tools._workspace import (
    OutsideWorkspaceError,
    resolve_in_workspace,
)
from pycodeloop.tools.filesystem import ReadFileTool, WriteFileTool
from pycodeloop.tools.http_request import HttpRequestTool
from pycodeloop.tools.web import WebFetchTool


class TestWorkspace(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.root = Path(self._tmpdir.name).resolve()
        self._cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self._cwd)

    def test_relative_path_resolves_inside_root(self):
        (self.root / "a.txt").write_text("hi\n")
        resolved = resolve_in_workspace("a.txt")
        self.assertEqual(resolved, self.root / "a.txt")

    def test_rejects_path_outside_root(self):
        outside = (
            Path(tempfile.gettempdir()).resolve() / "pycodeloop-outside-test"
        )
        with self.assertRaises(OutsideWorkspaceError):
            resolve_in_workspace(str(outside))

    def test_read_file_refuses_outside_workspace(self):
        outside = (
            Path(tempfile.gettempdir()).resolve() / "pycodeloop-outside-test"
        )
        outside.write_text("secret\n")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))

        result = ReadFileTool().run(path=str(outside))

        self.assertTrue(result.is_error)
        self.assertIn("outside workspace", result.output)

    def test_write_file_refuses_outside_workspace(self):
        outside = (
            Path(tempfile.gettempdir()).resolve() / "pycodeloop-outside-write"
        )
        result = WriteFileTool().run(path=str(outside), content="x\n")
        self.assertTrue(result.is_error)
        self.assertFalse(outside.exists())


class TestUrlSchemes(unittest.TestCase):
    def test_web_fetch_rejects_file_scheme(self):
        result = WebFetchTool().run(url="file:///etc/passwd")
        self.assertTrue(result.is_error)
        self.assertIn("http/https", result.output)

    def test_http_request_rejects_file_scheme(self):
        result = HttpRequestTool().run(url="file:///etc/passwd")
        self.assertTrue(result.is_error)
        self.assertIn("http/https", result.output)
