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
        return ToolResult(
            output=f"git {' '.join(args)} timed out", is_error=True
        )

    output = proc.stdout + proc.stderr

    return ToolResult(
        output=truncate(output.strip()) or "(no output)",
        is_error=proc.returncode != 0,
    )


class GitStatusTool(Tool):
    name = "git_status"
    description = "Show the working tree status (git status --porcelain)."
    operation = "read"
    parameters = {"type": "object", "properties": {}}

    def run(self) -> ToolResult:
        return _run_git("status", "--porcelain=v1", "--branch")


class GitDiffTool(Tool):
    name = "git_diff"
    description = "Show unstaged (or staged) changes as a unified diff."
    operation = "read"
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
    operation = "read"
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
        "Stage specific files and create a commit. `paths` is required — "
        "list every file to stage by name. Never stages the whole tree "
        "(no git add -A/-u)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Files to stage (required; no catch-all).",
            },
        },
        "required": ["message", "paths"],
    }
    operation = "execute_high_risk"

    def preview(
        self, message: str, paths: list[str] | None = None, **_
    ) -> str:
        paths = paths or []
        stat = (
            _run_git("diff", "--stat", "HEAD", "--", *paths) if paths else None
        )
        target = ", ".join(paths) if paths else "(no paths)"
        body = f"\n\n{stat.output}" if stat else ""
        return f"$ git commit -m {message!r} ({target}){body}"

    def run(self, message: str, paths: list[str] | None = None) -> ToolResult:
        if not paths:
            return ToolResult(
                output=(
                    "paths is required — pass the specific files to stage. "
                    "Refusing git add -A."
                ),
                is_error=True,
            )

        cleaned = [p for p in paths if p and p not in {"-A", "-u", "--all"}]
        if not cleaned or cleaned != list(paths):
            return ToolResult(
                output=(
                    "paths must be explicit file paths — "
                    "refusing catch-all flags like -A/-u."
                ),
                is_error=True,
            )

        add_result = _run_git("add", "--", *cleaned)

        if add_result.is_error:
            return add_result

        return _run_git("commit", "-m", message)
