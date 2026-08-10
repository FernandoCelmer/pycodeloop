"""Test filesystem, search and web Tool classes"""

import os
import tempfile
import unittest
from pathlib import Path

from codeloop.core.tools.filesystem import (
    DeleteFileTool,
    EditFileTool,
    ListDirTool,
    ReadFileTool,
    WriteFileTool,
)
from codeloop.core.tools.search import GlobTool, GrepTool


class ToolTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        # Real path (not a /tmp symlink like macOS's /var -> private/var) —
        # filesystem tools sandbox to the resolved cwd, and Path(x).resolve()
        # would otherwise stop matching str(self.tmp_path).
        self.tmp_path = Path(self._tmpdir.name).resolve()

        previous_cwd = os.getcwd()
        os.chdir(self.tmp_path)
        self.addCleanup(os.chdir, previous_cwd)


class TestReadFileTool(ToolTestCase):
    def test_write_then_read_file(self):
        target = self.tmp_path / "note.txt"
        WriteFileTool().run(path=str(target), content="line1\nline2\n")

        result = ReadFileTool().run(path=str(target))

        self.assertIn("1\tline1", result.output)
        self.assertIn("2\tline2", result.output)

    def test_rejects_path_outside_cwd(self):
        result = ReadFileTool().run(path="../outside.txt")

        self.assertTrue(result.is_error)
        self.assertIn("outside the project directory", result.output)

    def test_rejects_absolute_path_outside_cwd(self):
        result = ReadFileTool().run(path="/etc/hosts")

        self.assertTrue(result.is_error)
        self.assertIn("outside the project directory", result.output)


class TestWriteFileTool(ToolTestCase):
    def test_rejects_path_outside_cwd(self):
        result = WriteFileTool().run(path="/tmp/outside-codeloop-test.txt", content="x")

        self.assertTrue(result.is_error)
        self.assertIn("outside the project directory", result.output)


class TestEditFileTool(ToolTestCase):
    def test_replaces_unique_match(self):
        target = self.tmp_path / "note.txt"
        target.write_text("hello world")

        result = EditFileTool().run(
            path=str(target), old_string="world", new_string="codeloop"
        )

        self.assertFalse(result.is_error)
        self.assertEqual(target.read_text(), "hello codeloop")

    def test_rejects_ambiguous_match(self):
        target = self.tmp_path / "note.txt"
        target.write_text("foo foo")

        result = EditFileTool().run(
            path=str(target), old_string="foo", new_string="bar"
        )

        self.assertTrue(result.is_error)

    def test_rejects_path_outside_cwd(self):
        result = EditFileTool().run(
            path="../outside.txt", old_string="a", new_string="b"
        )

        self.assertTrue(result.is_error)
        self.assertIn("outside the project directory", result.output)


class TestDeleteFileTool(ToolTestCase):
    def test_deletes_file(self):
        target = self.tmp_path / "note.txt"
        target.write_text("bye")

        result = DeleteFileTool().run(path=str(target))

        self.assertFalse(result.is_error)
        self.assertFalse(target.exists())

    def test_reports_missing_file(self):
        result = DeleteFileTool().run(path=str(self.tmp_path / "missing.txt"))

        self.assertTrue(result.is_error)

    def test_preview_shows_removal_diff(self):
        target = self.tmp_path / "note.txt"
        target.write_text("bye\n")

        preview = DeleteFileTool().preview(path=str(target))

        self.assertIn("-bye", preview)

    def test_rejects_path_outside_cwd(self):
        result = DeleteFileTool().run(path="/etc/hosts")

        self.assertTrue(result.is_error)
        self.assertIn("outside the project directory", result.output)


class TestListDirTool(ToolTestCase):
    def test_list_dir(self):
        (self.tmp_path / "a.txt").write_text("")
        (self.tmp_path / "sub").mkdir()

        result = ListDirTool().run(path=str(self.tmp_path))

        self.assertIn("f a.txt", result.output)
        self.assertIn("d sub", result.output)


class TestGlobTool(ToolTestCase):
    def test_finds_matching_files(self):
        (self.tmp_path / "a.py").write_text("")
        (self.tmp_path / "b.txt").write_text("")

        result = GlobTool().run(pattern="*.py", path=str(self.tmp_path))

        self.assertIn("a.py", result.output)
        self.assertNotIn("b.txt", result.output)


class TestGrepTool(ToolTestCase):
    def test_finds_match(self):
        (self.tmp_path / "a.py").write_text("def hello():\n    pass\n")

        result = GrepTool().run(pattern="def hello", path=str(self.tmp_path))

        self.assertIn("a.py:1", result.output)


if __name__ == "__main__":
    unittest.main()
