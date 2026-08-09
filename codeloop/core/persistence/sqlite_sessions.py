"""SQLite Sessions (SQLAlchemy)"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import declarative_base, sessionmaker

from codeloop.abc.sessions import Sessions
from codeloop.core.session import Message, Session

Base = declarative_base()


class SessionRecord(Base):
    __tablename__ = "sessions"

    key = Column(String, primary_key=True)
    system_prompt = Column(String, nullable=False)
    cwd = Column(String, nullable=False)
    messages = Column(String, nullable=False)
    updated_at = Column(Float, nullable=False)
    message_count = Column(Integer, nullable=False)


class SqliteSessions(Sessions):
    """Session storage backed by a SQLAlchemy model in a single SQLite
    file. Defaults to `~/.codeloop/codeloop.db`, next to `config.json`
    — a generic, app-wide database file, not sessions-only, so other
    features can add their own tables to it later."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path.home() / ".codeloop" / "codeloop.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._engine = create_engine(f"sqlite:///{self.path}")
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    def _db(self) -> OrmSession:
        return self._session_factory()

    def post(self, key: str, session: Session) -> None:
        messages_json = json.dumps([asdict(m) for m in session.messages])

        with self._db() as db:
            record = db.get(SessionRecord, key)

            if record is None:
                record = SessionRecord(key=key)
                db.add(record)

            record.system_prompt = session.system_prompt
            record.cwd = session.cwd
            record.messages = messages_json
            record.updated_at = time.time()
            record.message_count = len(session.messages)

            db.commit()

    def get(self, key: str) -> Session | None:
        with self._db() as db:
            record = db.get(SessionRecord, key)

        if record is None:
            return None

        return Session(
            system_prompt=record.system_prompt,
            cwd=record.cwd,
            messages=[Message(**m) for m in json.loads(record.messages)],
        )

    def delete(self, key: str) -> None:
        with self._db() as db:
            record = db.get(SessionRecord, key)

            if record is not None:
                db.delete(record)
                db.commit()

    def list_sessions(self) -> dict:
        """key -> {updated_at, message_count, cwd}"""
        with self._db() as db:
            records = db.query(SessionRecord).all()

        return {
            r.key: {
                "updated_at": r.updated_at,
                "message_count": r.message_count,
                "cwd": r.cwd,
            }
            for r in records
        }
