"""Git Tools"""

from __future__ import annotations

import subprocess

from pycodeloop.abc.tool import Tool, ToolResult
from pycodeloop.tools._limits import truncate


def _run_git(*args: str, timeout: int = 30) -> ToolResult:
    try:
        proc = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return ToolResult(output="git is not installed", is_error=True)
    except subprocess.TimeoutExpired:
        return ToolResult(output=f"git {' '.join(args)} timed out", is_error=True)

    output = proc.stdout + proc.stderr

    return ToolResult(
        output=truncate(output.strip()) or "(no output)",
        is_error=proc.returncode != 0,
    )


class GitStatusTool(Tool):
    name = "git_status"
    description = "Show the working tree status (git status --porcelain)."
    parameters = {"type": "object", "properties": {}}

    def run(self) -> ToolResult:
        return _run_git("status", "--porcelain=v1", "--branch")


class GitDiffTool(Tool):
    name = "git_diff"
    description = "Show unstaged (or staged) changes as a unified diff."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "staged": {"type": "boolean", "default": False},
        },
    }

    def run(self, path: str = "", staged: bool = False) -> ToolResult:
        args = ["diff"]

        if staged:
            args.append("--staged")

        if path:
            args.extend(["--", path])

        return _run_git(*args)


class GitLogTool(Tool):
    name = "git_log"
    description = "Show recent commit history, one line per commit."
    parameters = {
        "type": "object",
        "properties": {
            "max_count": {"type": "integer", "default": 20},
            "path": {"type": "string"},
        },
    }

    def run(self, max_count: int = 20, path: str = "") -> ToolResult:
        args = ["log", f"-n{max_count}", "--oneline"]

        if path:
            args.extend(["--", path])

        return _run_git(*args)


class GitCommitTool(Tool):
    name = "git_commit"
    description = (
        "Stage files and create a commit. Pass `paths` to stage specific "
        "files, or omit it to stage everything (git add -A)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "paths": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["message"],
    }
    dangerous = True

    def preview(self, message: str, paths: list[str] | None = None, **_) -> str:
        stat = _run_git("diff", "--stat", "HEAD")
        target = ", ".join(paths) if paths else "all changes"
        return f"$ git commit -m {message!r} ({target})\n\n{stat.output}"

    def run(self, message: str, paths: list[str] | None = None) -> ToolResult:
        add_result = _run_git("add", *(paths or ["-A"]))

        if add_result.is_error:
            return add_result

        return _run_git("commit", "-m", message)
