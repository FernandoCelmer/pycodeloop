"""Test project memory (memory.py + Config wiring)"""

import tempfile
import unittest
from pathlib import Path

from pycodeloop.core.config import Config
from pycodeloop.core.memory import RememberTool, load_memory, memory_path, render_memory_prompt
from pycodeloop.providers import GenericProvider


class TestMemoryPath(unittest.TestCase):
    def test_load_memory_returns_empty_string_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_memory(tmp), "")

    def test_load_memory_reads_saved_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = memory_path(tmp)
            path.parent.mkdir(parents=True)
            path.write_text("- always use tabs\n")

            self.assertEqual(load_memory(tmp), "- always use tabs")

    def test_render_memory_prompt_empty_when_no_content(self):
        self.assertEqual(render_memory_prompt(""), "")

    def test_render_memory_prompt_includes_the_notes(self):
        prompt = render_memory_prompt("- note one\n- note two")

        self.assertIn("note one", prompt)
        self.assertIn("note two", prompt)


class TestRememberTool(unittest.TestCase):
    def test_appends_a_dated_bullet_and_creates_the_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = RememberTool(cwd=tmp)

            result = tool.run(note="user wants sharp corners, no border-radius")

            self.assertFalse(result.is_error)
            content = load_memory(tmp)
            self.assertIn("user wants sharp corners, no border-radius", content)
            self.assertTrue(content.startswith("- ("))

    def test_appending_twice_keeps_both_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = RememberTool(cwd=tmp)
            tool.run(note="first note")
            tool.run(note="second note")

            content = load_memory(tmp)

            self.assertIn("first note", content)
            self.assertIn("second note", content)

    def test_rejects_an_empty_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = RememberTool(cwd=tmp)

            result = tool.run(note="   ")

            self.assertTrue(result.is_error)


class TestConfigMemoryWiring(unittest.TestCase):
    def _provider(self) -> GenericProvider:
        return GenericProvider(url="http://fake/v1/chat/completions", model="fake-model")

    def test_remember_tool_present_by_default(self):
        config = Config(provider=self._provider(), storage=False)

        self.assertIn("remember", [t.name for t in config.tools])

    def test_memory_false_omits_the_tool(self):
        config = Config(provider=self._provider(), memory=False, storage=False)

        self.assertNotIn("remember", [t.name for t in config.tools])

    def test_existing_project_memory_is_folded_into_the_system_prompt(self):
        import os

        with tempfile.TemporaryDirectory() as tmp:
            path = memory_path(tmp)
            path.parent.mkdir(parents=True)
            path.write_text("- prefers terse commit messages\n")

            previous_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                config = Config(provider=self._provider(), storage=False)
            finally:
                os.chdir(previous_cwd)

            self.assertIn("prefers terse commit messages", config.system_prompt)


if __name__ == "__main__":
    unittest.main()
