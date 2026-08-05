from pathlib import Path

from aiflow.core.tools.filesystem import (
    EditFileTool,
    ListDirTool,
    ReadFileTool,
    WriteFileTool,
)
from aiflow.core.tools.search import GrepTool


def test_write_then_read_file(tmp_path: Path):
    target = tmp_path / "note.txt"
    WriteFileTool().run(path=str(target), content="line1\nline2\n")

    result = ReadFileTool().run(path=str(target))

    assert "1\tline1" in result.output
    assert "2\tline2" in result.output


def test_edit_file_replaces_unique_match(tmp_path: Path):
    target = tmp_path / "note.txt"
    target.write_text("hello world")

    result = EditFileTool().run(path=str(target), old_string="world", new_string="hermes")

    assert not result.is_error
    assert target.read_text() == "hello hermes"


def test_edit_file_rejects_ambiguous_match(tmp_path: Path):
    target = tmp_path / "note.txt"
    target.write_text("foo foo")

    result = EditFileTool().run(path=str(target), old_string="foo", new_string="bar")

    assert result.is_error


def test_list_dir(tmp_path: Path):
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "sub").mkdir()

    result = ListDirTool().run(path=str(tmp_path))

    assert "f a.txt" in result.output
    assert "d sub" in result.output


def test_grep_finds_match(tmp_path: Path):
    (tmp_path / "a.py").write_text("def hello():\n    pass\n")

    result = GrepTool().run(pattern="def hello", path=str(tmp_path))

    assert "a.py:1" in result.output
