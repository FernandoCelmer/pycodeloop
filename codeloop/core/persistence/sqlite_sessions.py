"""SQLite Storage"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path

from codeloop.abc.storage import Storage
from codeloop.core.session import Message, Session

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    key TEXT PRIMARY KEY,
    system_prompt TEXT NOT NULL,
    cwd TEXT NOT NULL,
    messages TEXT NOT NULL,
    updated_at REAL NOT NULL,
    message_count INTEGER NOT NULL
)
"""


class SqliteStorage(Storage):
    """
    Import:
        You can import the **SqliteStorage** class with:

            from codeloop.core.sqlite_storage import SqliteStorage

    Persists each `Session` as a row in a SQLite database — one file,
    queryable with plain SQL, no server to run. Defaults to
    `~/.codeloop/sessions.db`, next to `config.json`.

    Args:
        path (str | Path): Where the database file is written.
            Defaults to `~/.codeloop/sessions.db`.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path.home() / ".codeloop" / "sessions.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def post(self, key: str, session: Session) -> None:
        messages_json = json.dumps([asdict(m) for m in session.messages])

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions
                    (key, system_prompt, cwd, messages, updated_at, message_count)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    system_prompt = excluded.system_prompt,
                    cwd = excluded.cwd,
                    messages = excluded.messages,
                    updated_at = excluded.updated_at,
                    message_count = excluded.message_count
                """,
                (
                    key,
                    session.system_prompt,
                    session.cwd,
                    messages_json,
                    time.time(),
                    len(session.messages),
                ),
            )

    def get(self, key: str) -> Session | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT system_prompt, cwd, messages FROM sessions WHERE key = ?",
                (key,),
            ).fetchone()

        if row is None:
            return None

        system_prompt, cwd, messages_json = row

        return Session(
            system_prompt=system_prompt,
            cwd=cwd,
            messages=[Message(**m) for m in json.loads(messages_json)],
        )

    def delete(self, key: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE key = ?", (key,))

    def list_sessions(self) -> dict:
        """Return the saved-session index: key -> {updated_at,
        message_count, cwd}."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, updated_at, message_count, cwd FROM sessions"
            ).fetchall()

        return {
            key: {"updated_at": updated_at, "message_count": count, "cwd": cwd}
            for key, updated_at, count, cwd in rows
        }
