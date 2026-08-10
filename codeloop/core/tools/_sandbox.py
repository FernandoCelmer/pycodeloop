"""Confines filesystem tool access to the current working directory —
without it, a path like `../../../.ssh/id_rsa` or an absolute path
outside the project is read/written exactly like any other."""

from __future__ import annotations

from pathlib import Path


class PathEscapesSandbox(Exception):
    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"'{path}' is outside the project directory")


def resolve_in_sandbox(path: str) -> Path:
    """Resolve `path` (relative or absolute, symlinks included) and
    raise `PathEscapesSandbox` if it falls outside the current working
    directory."""
    cwd = Path.cwd().resolve()
    resolved = (cwd / path).resolve()

    if resolved != cwd and not resolved.is_relative_to(cwd):
        raise PathEscapesSandbox(path)

    return resolved
