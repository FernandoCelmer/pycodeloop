"""Unit tests for the CI run-result model and exit-code mapping."""

from __future__ import annotations

import unittest

from pycodeloop.cli.commands.run_result import (
    EXIT_CODE_BUDGET,
    EXIT_CODE_ERROR,
    EXIT_CODE_REGRESSION,
    EXIT_CODE_SUCCESS,
    RunResult,
    exit_code_for,
    files_modified_from,
)


class _Record:
    def __init__(self, path: str, action: str) -> None:
        self.path = path
        self.action = action


class TestRunResultSerialization(unittest.TestCase):
    def test_to_dict_matches_issue_shape(self):
        result = RunResult(
            status="success",
            turns=3,
            tokens={"input": 12400, "output": 2100},
            cost_usd=0.042,
            regression=False,
            files_modified=["src/auth.py"],
            text="done",
        )

        data = result.to_dict()

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["turns"], 3)
        self.assertEqual(data["tokens"], {"input": 12400, "output": 2100})
        self.assertEqual(data["cost_usd"], 0.042)
        self.assertFalse(data["regression"])
        self.assertEqual(data["files_modified"], ["src/auth.py"])


class TestExitCodeMapping(unittest.TestCase):
    def test_success_is_zero(self):
        self.assertEqual(
            exit_code_for(RunResult(status="success")), EXIT_CODE_SUCCESS
        )

    def test_error_max_turns_cancelled_are_one(self):
        for status in ("error", "max_turns", "cancelled"):
            self.assertEqual(
                exit_code_for(RunResult(status=status)), EXIT_CODE_ERROR
            )

    def test_regression_is_two(self):
        self.assertEqual(
            exit_code_for(RunResult(status="success", regression=True)),
            EXIT_CODE_REGRESSION,
        )

    def test_budget_is_three(self):
        self.assertEqual(
            exit_code_for(RunResult(status="budget")), EXIT_CODE_BUDGET
        )


class TestFilesModified(unittest.TestCase):
    def test_collects_only_modifying_actions(self):
        history = [
            _Record("a.py", "read"),
            _Record("a.py", "write"),
            _Record("b.py", "edit"),
            _Record("c.py", "read"),
            _Record("b.py", "delete"),
        ]

        self.assertEqual(files_modified_from(history), ["a.py", "b.py"])

    def test_dedupes_paths(self):
        history = [
            _Record("a.py", "write"),
            _Record("a.py", "edit"),
        ]

        self.assertEqual(files_modified_from(history), ["a.py"])


if __name__ == "__main__":
    unittest.main()
