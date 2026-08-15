"""SQLite Sessions (SQLAlchemy)"""

from __future__ import annotations

import json
import time
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from pycodeloop.abc.sessions import Sessions
from pycodeloop.core.session import Message, Session
from pycodeloop.store.models.base import Base
from pycodeloop.store.models.message_record import MessageRecord
from pycodeloop.store.models.session_record import SessionRecord


class SqliteSessions(Sessions):
    """Session storage backed by SQLAlchemy models in a single SQLite
    file. Defaults to `~/.pycodeloop/pycodeloop.db`, next to `config.json`
    — a generic, app-wide database file, not sessions-only, so other
    features can add their own tables to it later."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path.home() / ".pycodeloop" / "pycodeloop.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._engine = create_engine(
            f"sqlite:///{self.path}", poolclass=NullPool
        )
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(
            bind=self._engine, expire_on_commit=False
        )
        self._migrate_legacy_messages()
        self._migrate_images_column()
        self._session_identity: dict[str, int] = {}

    def _db(self) -> OrmSession:
        return self._session_factory()

    def _migrate_images_column(self) -> None:
        """`create_all()` only creates missing tables, not missing
        columns on an existing one — add `images` for databases created
        before message attachments existed."""
        with self._engine.connect() as conn:
            columns = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(messages)"))
            }
        if "images" in columns:
            return

        with self._engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE messages ADD COLUMN images VARCHAR")
            )

    def _migrate_legacy_messages(self) -> None:
        """One-time backfill from the old single-blob `sessions.messages`
        column (pre-normalization) into the `messages` table, then drop
        that column — it's `NOT NULL` in the old schema, so leaving it
        behind would break every future insert."""
        with self._engine.connect() as conn:
            columns = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(sessions)"))
            }
        if "messages" not in columns:
            return

        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT key, messages FROM sessions WHERE messages IS NOT NULL"
                )
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

    def close(self) -> None:
        self._engine.dispose()

    def post(self, key: str, session: Session) -> None:
        """Persists `session`, writing only the messages appended since
        the last save when possible — the common case, since `on_message`
        fires after every message including every tool result. Falls
        back to a full delete-and-reinsert when the session is new, a
        *different* `Session` object is posted for a key we've already
        saved (an intentional overwrite, not the same object growing —
        checked via identity, since a message-count watermark alone
        can't tell the two apart), `session.dirty` (compaction/trim/
        repair replaced or reordered existing messages, not just
        appended), or the message count shrank."""
        with self._db() as db:
            record = db.get(SessionRecord, key)
            is_new = record is None

            if is_new:
                record = SessionRecord(key=key)
                db.add(record)

            record.system_prompt = session.system_prompt
            record.cwd = session.cwd
            record.updated_at = time.time()

            previous_count = 0 if is_new else record.message_count
            same_object = self._session_identity.get(key) == id(session)
            full_rewrite = (
                is_new
                or not same_object
                or session.dirty
                or len(session.messages) < previous_count
            )
            record.message_count = len(session.messages)

            if full_rewrite:
                db.query(MessageRecord).filter(
                    MessageRecord.session_key == key
                ).delete()
                new_messages = list(enumerate(session.messages))
            else:
                new_messages = list(
                    enumerate(
                        session.messages[previous_count:],
                        start=previous_count,
                    )
                )

            for position, message in new_messages:
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
                        images=(
                            json.dumps(message.images)
                            if message.images
                            else None
                        ),
                    )
                )

            db.commit()
            session.dirty = False
            self._session_identity[key] = id(session)

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
                        tool_calls=(
                            json.loads(row.tool_calls)
                            if row.tool_calls
                            else None
                        ),
                        images=json.loads(row.images) if row.images else None,
                    )
                    for row in rows
                ],
            )

    def delete(self, key: str) -> None:
        self._session_identity.pop(key, None)
        with self._db() as db:
            record = db.get(SessionRecord, key)

            if record is not None:
                db.delete(record)

            db.query(MessageRecord).filter(
                MessageRecord.session_key == key
            ).delete()
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
