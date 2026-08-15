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


class OutsideWorkspaceError(ValueError):
    def __init__(self, path: str, root: Path) -> None:
        self.path = path
        self.root = root
        super().__init__(
            f"Refused path {path!r}: outside workspace root {root}"
        )


def workspace_root() -> Path:
    return Path.cwd().resolve()


def resolve_in_workspace(
    path: str, root: Path | None = None, enabled: bool = True
) -> Path:
    """Resolve `path` under `root` (default: cwd). Raises
    `OutsideWorkspaceError` if the resolved path escapes the root via
    `..` or an absolute path outside it — unless `enabled` is False, in
    which case `path` resolves as-is with no restriction.

    `enabled` is a plain parameter, not process-wide state — each tool
    instance decides for itself so two `Config`s with different
    `workspace=` settings (or tests running in the same process) can't
    interfere with each other."""
    target = Path(path).expanduser()
    base = (root or workspace_root()).resolve()

    if not enabled:
        return (
            target.resolve()
            if target.is_absolute()
            else (base / target).resolve()
        )

    if not target.is_absolute():
        target = base / target
    resolved = target.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise OutsideWorkspaceError(path, base) from exc
    return resolved
