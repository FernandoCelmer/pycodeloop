"""Test workspace path jail and URL scheme guards."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pycodeloop.store.file_access_log import FileAccessLog
from pycodeloop.tools._workspace import (
    OutsideWorkspaceError,
    is_workspace_enabled,
    resolve_in_workspace,
    set_workspace_enabled,
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


class TestWorkspaceToggle(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.root = Path(self._tmpdir.name).resolve()
        self._cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self._cwd)
        self.addCleanup(set_workspace_enabled, True)

        # A second, unrelated tmp dir standing in for "outside the
        # workspace" — freshly random per test run, unlike a fixed name
        # under the shared system tempdir, which the read-cache in
        # file_access_log would treat as "unchanged" on a repeat run.
        self._outside_tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._outside_tmpdir.cleanup)
        self.outside_dir = Path(self._outside_tmpdir.name).resolve()

        access_log = FileAccessLog(path=self.root / "access.db")
        log_patcher = mock.patch(
            "pycodeloop.tools.filesystem.default_log", access_log
        )
        log_patcher.start()
        self.addCleanup(log_patcher.stop)

    def test_enabled_by_default(self):
        self.assertTrue(is_workspace_enabled())

    def test_disabled_lets_paths_outside_root_resolve(self):
        outside = self.outside_dir / "toggle-test"
        set_workspace_enabled(False)

        resolved = resolve_in_workspace(str(outside))

        self.assertEqual(resolved, outside)

    def test_disabled_lets_read_file_read_outside_workspace(self):
        outside = self.outside_dir / "toggle-read"
        outside.write_text("secret\n")
        set_workspace_enabled(False)

        result = ReadFileTool().run(path=str(outside))

        self.assertFalse(result.is_error)
        self.assertIn("secret", result.output)

    def test_re_enabling_restores_the_jail(self):
        outside = self.outside_dir / "toggle-back"
        set_workspace_enabled(False)
        set_workspace_enabled(True)

        with self.assertRaises(OutsideWorkspaceError):
            resolve_in_workspace(str(outside))


class TestUrlSchemes(unittest.TestCase):
    def test_web_fetch_rejects_file_scheme(self):
        result = WebFetchTool().run(url="file:///etc/passwd")
        self.assertTrue(result.is_error)
        self.assertIn("http/https", result.output)

    def test_http_request_rejects_file_scheme(self):
        result = HttpRequestTool().run(url="file:///etc/passwd")
        self.assertTrue(result.is_error)
        self.assertIn("http/https", result.output)
