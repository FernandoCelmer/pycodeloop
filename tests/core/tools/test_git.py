"""Test git Tool classes"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from aiflow.core.tools.git import (
    GitCommitTool,
    GitDiffTool,
    GitLogTool,
    GitStatusTool,
)


class GitToolTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.repo = Path(self._tmpdir.name)
        self._cwd = Path.cwd()
        self.addCleanup(os.chdir, self._cwd)

        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=self.repo, check=True
        )
        (self.repo / "a.txt").write_text("hello\n")
        subprocess.run(["git", "add", "-A"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=self.repo, check=True)

        os.chdir(self.repo)


class TestGitStatusTool(GitToolTestCase):
    def test_reports_clean_tree(self):
        result = GitStatusTool().run()

        self.assertFalse(result.is_error)

    def test_reports_untracked_file(self):
        (self.repo / "b.txt").write_text("new\n")

        result = GitStatusTool().run()

        self.assertIn("b.txt", result.output)


class TestGitDiffTool(GitToolTestCase):
    def test_shows_unstaged_changes(self):
        (self.repo / "a.txt").write_text("changed\n")

        result = GitDiffTool().run()

        self.assertIn("changed", result.output)


class TestGitLogTool(GitToolTestCase):
    def test_shows_commit(self):
        result = GitLogTool().run()

        self.assertIn("init", result.output)


class TestGitCommitTool(GitToolTestCase):
    def test_commits_staged_changes(self):
        (self.repo / "a.txt").write_text("v2\n")

        result = GitCommitTool().run(message="update a.txt")

        self.assertFalse(result.is_error)
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )
        self.assertIn("update a.txt", log.stdout)

    def test_preview_shows_diff_stat(self):
        (self.repo / "a.txt").write_text("v2\n")

        preview = GitCommitTool().preview(message="update a.txt")

        self.assertIn("update a.txt", preview)
        self.assertIn("a.txt", preview)


if __name__ == "__main__":
    unittest.main()
