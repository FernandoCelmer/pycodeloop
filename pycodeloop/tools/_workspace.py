"""Workspace root helpers — keep filesystem tools inside the process cwd
unless the caller opts out. Paths may be relative or absolute; absolute
paths outside the root are rejected."""

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


def resolve_in_workspace(path: str, root: Path | None = None) -> Path:
    """Resolve `path` under `root` (default: cwd). Raises
    `OutsideWorkspaceError` if the resolved path escapes the root via
    `..` or an absolute path outside it."""
    base = (root or workspace_root()).resolve()
    target = Path(path).expanduser()
    if not target.is_absolute():
        target = base / target
    resolved = target.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise OutsideWorkspaceError(path, base) from exc
    return resolved
