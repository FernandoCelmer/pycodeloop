"""Workspace root helpers — keep filesystem tools inside the process cwd
unless the caller opts out. Paths may be relative or absolute; absolute
paths outside the root are rejected.

This only covers tools that take a structured `path` argument
(read_file, write_file, edit_file, delete_file, grep, glob). `bash` and
`git` run arbitrary shell/subprocess commands with no path parsing, so
they are never restricted by this jail regardless of the toggle below
— the only guardrail on them is the `dangerous` confirm gate (removed
entirely by `--yes`)."""

from __future__ import annotations

from pathlib import Path

_enabled = True


class OutsideWorkspaceError(ValueError):
    def __init__(self, path: str, root: Path) -> None:
        self.path = path
        self.root = root
        super().__init__(
            f"Refused path {path!r}: outside workspace root {root}"
        )


def set_workspace_enabled(enabled: bool) -> None:
    """Toggle the jail process-wide. Callers doing this mid-run (rather
    than once at startup via `Config(workspace=...)`) should know it
    affects every tool call from that point on, not just their own."""
    global _enabled
    _enabled = enabled


def is_workspace_enabled() -> bool:
    return _enabled


def workspace_root() -> Path:
    return Path.cwd().resolve()


def resolve_in_workspace(path: str, root: Path | None = None) -> Path:
    """Resolve `path` under `root` (default: cwd). Raises
    `OutsideWorkspaceError` if the resolved path escapes the root via
    `..` or an absolute path outside it — unless the jail was disabled
    via `set_workspace_enabled(False)`, in which case `path` resolves
    as-is with no restriction."""
    target = Path(path).expanduser()

    if not _enabled:
        base = (root or workspace_root()).resolve()
        return (
            target.resolve()
            if target.is_absolute()
            else (base / target).resolve()
        )

    base = (root or workspace_root()).resolve()
    if not target.is_absolute():
        target = base / target
    resolved = target.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise OutsideWorkspaceError(path, base) from exc
    return resolved
