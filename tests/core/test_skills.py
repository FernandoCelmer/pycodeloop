"""Test skills discovery and ReadSkillTool"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import codeloop.core.local_config as local_config
from codeloop.core.skills import (
    ReadSkillTool,
    discover_skills,
    render_skills_index,
)


class SkillsTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp_path = Path(self._tmpdir.name)
        self.home_path = self.tmp_path / "home"

        patcher = mock.patch.object(
            local_config, "CONFIG_PATH", self.tmp_path / "config.json"
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write(self, relative: str, content: str) -> None:
        path = self.tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def _discover(self, sources=None, use_cache=True):
        return discover_skills(
            cwd=self.tmp_path,
            home=self.home_path,
            sources=sources,
            use_cache=use_cache,
        )


class TestDiscoverSkills(SkillsTestCase):
    def test_finds_claude_skill_md(self):
        self._write(
            ".claude/skills/mytest/SKILL.md",
            "---\nname: mytest\ndescription: A test skill\n---\n\nDo the thing.\n",
        )

        skills = self._discover(sources={"claude-skill"})

        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].name, "mytest")
        self.assertEqual(skills[0].description, "A test skill")
        self.assertEqual(skills[0].content, "Do the thing.")

    def test_finds_claude_memory(self):
        self._write("CLAUDE.md", "# Project rules\n\nBe terse.\n")

        skills = self._discover(sources={"claude-memory"})

        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].name, "CLAUDE.md")
        self.assertEqual(skills[0].source, "claude-memory")

    def test_finds_cursor_rule(self):
        self._write(
            ".cursor/rules/style.mdc",
            "---\ndescription: Style rules\nalwaysApply: true\n---\n\n"
            "Use snake_case.\n",
        )

        skills = self._discover(sources={"cursor-rule"})

        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].name, "style")
        self.assertEqual(skills[0].description, "Style rules")

    def test_finds_agents_md(self):
        self._write("AGENTS.md", "# Agent instructions\n\nBe terse.\n")

        skills = self._discover(sources={"agents-md"})

        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].source, "agents-md")

    def test_empty_when_nothing_found(self):
        self.assertEqual(self._discover(), [])


class TestSkillsCache(SkillsTestCase):
    def test_second_call_is_served_from_cache(self):
        self._write(
            ".claude/skills/a/SKILL.md",
            "---\nname: a\ndescription: does a\n---\n\nbody\n",
        )

        first = self._discover(sources={"claude-skill"})
        cache = local_config.get_section("skills")
        self.assertEqual(len(cache), 1)

        second = self._discover(sources={"claude-skill"})

        self.assertEqual([s.name for s in first], [s.name for s in second])

    def test_cache_invalidates_when_file_changes(self):
        skill_path = self.tmp_path / ".claude" / "skills" / "a" / "SKILL.md"
        self._write(
            ".claude/skills/a/SKILL.md",
            "---\nname: a\ndescription: v1\n---\n\nbody\n",
        )
        self._discover(sources={"claude-skill"})

        skill_path.write_text("---\nname: a\ndescription: v2\n---\n\nbody\n")
        skill_path.touch()

        skills = self._discover(sources={"claude-skill"})

        self.assertEqual(skills[0].description, "v2")

    def test_use_cache_false_skips_cache_entirely(self):
        self._write(
            ".claude/skills/a/SKILL.md",
            "---\nname: a\ndescription: v1\n---\n\nbody\n",
        )

        skills = self._discover(sources={"claude-skill"}, use_cache=False)

        self.assertEqual(skills[0].name, "a")
        self.assertEqual(local_config.get_section("skills"), {})


class TestRenderSkillsIndex(SkillsTestCase):
    def test_lists_each_skill(self):
        self._write(
            ".claude/skills/a/SKILL.md",
            "---\nname: a\ndescription: does a\n---\n\nbody\n",
        )

        skills = self._discover(sources={"claude-skill"})
        index = render_skills_index(skills)

        self.assertIn("read_skill", index)
        self.assertIn("**a** (claude-skill): does a", index)

    def test_empty_for_no_skills(self):
        self.assertEqual(render_skills_index([]), "")


class TestReadSkillTool(SkillsTestCase):
    def test_returns_content(self):
        self._write(
            ".claude/skills/a/SKILL.md",
            "---\nname: a\ndescription: does a\n---\n\nfull instructions here\n",
        )
        skills = self._discover(sources={"claude-skill"})
        tool = ReadSkillTool(skills)

        result = tool.run(name="a")

        self.assertFalse(result.is_error)
        self.assertEqual(result.output, "full instructions here")

    def test_reports_unknown_skill(self):
        tool = ReadSkillTool([])

        result = tool.run(name="missing")

        self.assertTrue(result.is_error)
        self.assertIn("Unknown skill", result.output)


if __name__ == "__main__":
    unittest.main()
