"""File Storage"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from codeloop.abc.storage import Storage
from codeloop.core.session import Message, Session


class FileStorage(Storage):
    """
    Import:
        You can import the **FileStorage** class with:

            from codeloop.core.storage import FileStorage

    Persists each `Session` as a JSON file under `directory`, one file
    per key — the simplest way to resume a conversation across process
    restarts without a database.

    Args:
        directory (str | Path): Where session files are written.
            Defaults to `~/.codeloop/sessions/`.
    """

    def __init__(self, directory: str | Path | None = None) -> None:
        self.directory = Path(directory or Path.home() / ".codeloop" / "sessions")

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def post(self, key: str, session: Session) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        data = {
            "system_prompt": session.system_prompt,
            "cwd": session.cwd,
            "messages": [asdict(message) for message in session.messages],
        }
        self._path(key).write_text(json.dumps(data, indent=2))

    def get(self, key: str) -> Session | None:
        path = self._path(key)
        if not path.exists():
            return None

        data = json.loads(path.read_text())
        return Session(
            system_prompt=data["system_prompt"],
            cwd=data["cwd"],
            messages=[Message(**message) for message in data["messages"]],
        )

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)
