"""Local Config — JSON-file-backed Settings store"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

from codeloop.abc.settings import Settings

DEFAULT_PATH = Path.home() / ".codeloop" / "config.json"


class JsonFileStore(Settings):
    """`Settings` store backed by a single JSON file — defaults to
    `~/.codeloop/config.json`."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or DEFAULT_PATH)

    def read(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            self.path.write_text(json.dumps(data, indent=2))

    def get_section(self, name: str) -> dict:
        return self.read().get(name, {})

    def set_section(self, name: str, value: dict) -> None:
        data = self.read()
        data[name] = value

        self.write(data)


default_store = JsonFileStore()
