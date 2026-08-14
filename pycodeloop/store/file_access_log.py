"""Per-session log of files read/written/edited/deleted, backed by the
same SQLite file as `SqliteSessions` — lets `read_file` skip re-emitting
content the agent was already shown unchanged (saves tokens) and gives a
queryable audit trail of file activity per session."""

from __future__ import annotations

import contextvars
import time
from pathlib import Path

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from pycodeloop.store.models.base import Base
from pycodeloop.store.models.file_access_record import FileAccessRecord

_current_session_key: contextvars.ContextVar[str] = contextvars.ContextVar(
    "pycodeloop_session_key", default="global"
)


def current_session_key() -> str:
    return _current_session_key.get()


class session_scope:
    """Binds the active `session_key` for the duration of one turn, so
    filesystem tools can log against it without `session_key` being
    threaded through every `Tool.run()` call. Use as:

        with session_scope(session_key or "global"):
            agent.run(...)
    """

    def __init__(self, session_key: str) -> None:
        self._session_key = session_key
        self._token: contextvars.Token | None = None

    def __enter__(self) -> None:
        self._token = _current_session_key.set(self._session_key)

    def __exit__(self, *_exc) -> None:
        if self._token is not None:
            _current_session_key.reset(self._token)


class FileAccessLog:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path.home() / ".pycodeloop" / "pycodeloop.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._engine = create_engine(f"sqlite:///{self.path}")
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    def record(
        self,
        path: str,
        action: str,
        content_hash: str | None = None,
        size: int | None = None,
        offset: int | None = None,
        limit: int | None = None,
        session_key: str | None = None,
    ) -> None:
        with self._session_factory() as db:
            db.add(
                FileAccessRecord(
                    session_key=session_key or current_session_key(),
                    path=path,
                    action=action,
                    offset=offset,
                    limit=limit,
                    content_hash=content_hash,
                    size=size,
                    accessed_at=time.time(),
                )
            )
            db.commit()

    def last_record(
        self, path: str, session_key: str | None = None
    ) -> FileAccessRecord | None:
        with self._session_factory() as db:
            return (
                db.query(FileAccessRecord)
                .filter(
                    FileAccessRecord.session_key == (session_key or current_session_key()),
                    FileAccessRecord.path == path,
                )
                .order_by(desc(FileAccessRecord.id))
                .first()
            )

    def history(self, session_key: str, limit: int = 100) -> list[FileAccessRecord]:
        with self._session_factory() as db:
            return (
                db.query(FileAccessRecord)
                .filter(FileAccessRecord.session_key == session_key)
                .order_by(desc(FileAccessRecord.id))
                .limit(limit)
                .all()
            )


default_log = FileAccessLog()
