"""SQLite Sessions (SQLAlchemy)"""

from __future__ import annotations

import json
import time
from pathlib import Path

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
    text,
)
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
    updated_at = Column(Float, nullable=False)
    message_count = Column(Integer, nullable=False)


class MessageRecord(Base):
    """One row per message — kept out of a JSON blob so the conversation
    is actually readable/queryable from a plain SQL client."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_key = Column(String, ForeignKey("sessions.key"), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    tool_call_id = Column(String, nullable=True)
    tool_calls = Column(String, nullable=True)


class SqliteSessions(Sessions):
    """Session storage backed by SQLAlchemy models in a single SQLite
    file. Defaults to `~/.codeloop/codeloop.db`, next to `config.json`
    — a generic, app-wide database file, not sessions-only, so other
    features can add their own tables to it later."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path.home() / ".codeloop" / "codeloop.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._engine = create_engine(f"sqlite:///{self.path}")
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)
        self._migrate_legacy_messages()

    def _db(self) -> OrmSession:
        return self._session_factory()

    def _migrate_legacy_messages(self) -> None:
        """One-time backfill from the old single-blob `sessions.messages`
        column (pre-normalization) into the `messages` table, then drop
        that column — it's `NOT NULL` in the old schema, so leaving it
        behind would break every future insert."""
        with self._engine.connect() as conn:
            columns = {
                row[1] for row in conn.execute(text("PRAGMA table_info(sessions)"))
            }
        if "messages" not in columns:
            return

        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT key, messages FROM sessions WHERE messages IS NOT NULL")
            ).fetchall()

        if rows:
            with self._db() as db:
                for key, blob in rows:
                    already_migrated = (
                        db.query(MessageRecord)
                        .filter(MessageRecord.session_key == key)
                        .first()
                        is not None
                    )
                    if already_migrated:
                        continue

                    try:
                        items = json.loads(blob)
                    except (TypeError, ValueError):
                        continue

                    for position, item in enumerate(items):
                        db.add(
                            MessageRecord(
                                session_key=key,
                                position=position,
                                role=item.get("role", ""),
                                content=str(item.get("content", "")),
                                tool_call_id=item.get("tool_call_id"),
                                tool_calls=(
                                    json.dumps(item["tool_calls"])
                                    if item.get("tool_calls")
                                    else None
                                ),
                            )
                        )
                db.commit()

        with self._engine.begin() as conn:
            conn.execute(text("ALTER TABLE sessions DROP COLUMN messages"))

    def post(self, key: str, session: Session) -> None:
        with self._db() as db:
            record = db.get(SessionRecord, key)

            if record is None:
                record = SessionRecord(key=key)
                db.add(record)

            record.system_prompt = session.system_prompt
            record.cwd = session.cwd
            record.updated_at = time.time()
            record.message_count = len(session.messages)

            db.query(MessageRecord).filter(MessageRecord.session_key == key).delete()
            for position, message in enumerate(session.messages):
                db.add(
                    MessageRecord(
                        session_key=key,
                        position=position,
                        role=message.role,
                        content=str(message.content),
                        tool_call_id=message.tool_call_id,
                        tool_calls=(
                            json.dumps(message.tool_calls)
                            if message.tool_calls
                            else None
                        ),
                    )
                )

            db.commit()

    def get(self, key: str) -> Session | None:
        with self._db() as db:
            record = db.get(SessionRecord, key)

            if record is None:
                return None

            rows = (
                db.query(MessageRecord)
                .filter(MessageRecord.session_key == key)
                .order_by(MessageRecord.position)
                .all()
            )

            return Session(
                system_prompt=record.system_prompt,
                cwd=record.cwd,
                messages=[
                    Message(
                        role=row.role,
                        content=row.content,
                        tool_call_id=row.tool_call_id,
                        tool_calls=json.loads(row.tool_calls)
                        if row.tool_calls
                        else None,
                    )
                    for row in rows
                ],
            )

    def delete(self, key: str) -> None:
        with self._db() as db:
            record = db.get(SessionRecord, key)

            if record is not None:
                db.delete(record)

            db.query(MessageRecord).filter(MessageRecord.session_key == key).delete()
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
