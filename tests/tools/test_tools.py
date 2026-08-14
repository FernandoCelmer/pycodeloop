"""Test filesystem, search and web Tool classes"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pycodeloop.store.file_access_log import FileAccessLog
from pycodeloop.tools.filesystem import (
    DeleteFileTool,
    EditFileTool,
    ListDirTool,
    ReadFileTool,
    WriteFileTool,
)
from pycodeloop.tools.search import GlobTool, GrepTool


class ToolTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp_path = Path(self._tmpdir.name).resolve()

        previous_cwd = os.getcwd()
        os.chdir(self.tmp_path)
        self.addCleanup(os.chdir, previous_cwd)

        self._logdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._logdir.cleanup)
        self.access_log = FileAccessLog(path=Path(self._logdir.name) / "access.db")
        patcher = mock.patch("pycodeloop.tools.filesystem.default_log", self.access_log)
        patcher.start()
        self.addCleanup(patcher.stop)


class TestReadFileTool(ToolTestCase):
    def test_write_then_read_file(self):
        target = self.tmp_path / "note.txt"
        WriteFileTool().run(path=str(target), content="line1\nline2\n")

        result = ReadFileTool().run(path=str(target))

        self.assertIn("1\tline1", result.output)
        self.assertIn("2\tline2", result.output)

    def test_second_identical_read_is_a_short_notice(self):
        target = self.tmp_path / "note.txt"
        target.write_text("line1\nline2\n")
        tool = ReadFileTool()

        first = tool.run(path=str(target))
        second = tool.run(path=str(target))

        self.assertIn("1\tline1", first.output)
        self.assertIn("unchanged since you last read", second.output)
        self.assertNotIn("line1", second.output)

    def test_force_shows_full_content_even_if_unchanged(self):
        target = self.tmp_path / "note.txt"
        target.write_text("line1\n")
        tool = ReadFileTool()
        tool.run(path=str(target))

        result = tool.run(path=str(target), force=True)

        self.assertIn("1\tline1", result.output)

    def test_read_after_edit_shows_full_content_not_a_cache_hit(self):
        target = self.tmp_path / "note.txt"
        target.write_text("line1\n")
        read_tool = ReadFileTool()
        read_tool.run(path=str(target))

        EditFileTool().run(path=str(target), old_string="line1", new_string="line2")
        result = read_tool.run(path=str(target))

        self.assertIn("1\tline2", result.output)

    def test_different_offset_is_not_a_cache_hit(self):
        target = self.tmp_path / "note.txt"
        target.write_text("line1\nline2\nline3\n")
        tool = ReadFileTool()
        tool.run(path=str(target))

        result = tool.run(path=str(target), offset=2)

        self.assertIn("2\tline2", result.output)


class TestEditFileTool(ToolTestCase):
    def test_replaces_unique_match(self):
        target = self.tmp_path / "note.txt"
        target.write_text("hello world")

        result = EditFileTool().run(
            path=str(target), old_string="world", new_string="pycodeloop"
        )

        self.assertFalse(result.is_error)
        self.assertEqual(target.read_text(), "hello pycodeloop")

    def test_rejects_ambiguous_match(self):
        target = self.tmp_path / "note.txt"
        target.write_text("foo foo")

        result = EditFileTool().run(
            path=str(target), old_string="foo", new_string="bar"
        )

        self.assertTrue(result.is_error)


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

    def test_skips_binary_files(self):
        (self.tmp_path / "data.bin").write_bytes(b"\x00\x01hello\x00")
        (self.tmp_path / "a.py").write_text("hello\n")

        result = GrepTool().run(pattern="hello", path=str(self.tmp_path))

        self.assertIn("a.py:1", result.output)
        self.assertNotIn("data.bin", result.output)


if __name__ == "__main__":
    unittest.main()
