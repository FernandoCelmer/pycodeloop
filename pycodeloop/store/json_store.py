"""Local Config — JSON-file-backed Settings store"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path

from pycodeloop.abc.settings import Settings

DEFAULT_PATH = Path.home() / ".pycodeloop" / "config.json"


class JsonFileStore(Settings):
    """`Settings` store backed by a single JSON file — defaults to
    `~/.pycodeloop/config.json`."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or DEFAULT_PATH)

    def read(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def write(self, data: dict) -> None:
        """Write via a temp file + atomic rename — a crash or concurrent
        writer mid-write can otherwise leave `config.json` truncated or
        corrupt, and the next `read()` would silently discard every
        previously saved section instead of just this write."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=self.path.parent, prefix=f".{self.path.name}."
            )
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(json.dumps(data, indent=2))
                os.replace(tmp_path, self.path)
            except OSError:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
                raise
        except OSError:
            with contextlib.suppress(OSError):
                self.path.write_text(json.dumps(data, indent=2))

    def get_section(self, name: str) -> dict:
        return self.read().get(name, {})

    def set_section(self, name: str, value: dict) -> None:
        data = self.read()
        data[name] = value

        self.write(data)


default_store = JsonFileStore()
