"""File Storage"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from codeloop.abc.storage import Storage
from codeloop.core.local_config import get_section, set_section
from codeloop.core.session import Message, Session

_SESSIONS_SECTION = "sessions"


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
        self._index(key, session)

    def _index(self, key: str, session: Session) -> None:
        """Record key/updated_at/message_count in ~/.codeloop/config.json
        under "sessions", so `FileStorage.list_sessions()` (and CLI
        tooling built on it) can list saved conversations without
        reading every session file."""
        sessions = get_section(_SESSIONS_SECTION)
        sessions[key] = {
            "updated_at": time.time(),
            "message_count": len(session.messages),
            "cwd": session.cwd,
        }

        set_section(_SESSIONS_SECTION, sessions)

    @staticmethod
    def list_sessions() -> dict:
        """Return the saved-session index: key -> {updated_at,
        message_count, cwd}."""
        return get_section(_SESSIONS_SECTION)

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

        sessions = get_section(_SESSIONS_SECTION)
        sessions.pop(key, None)

        set_section(_SESSIONS_SECTION, sessions)
