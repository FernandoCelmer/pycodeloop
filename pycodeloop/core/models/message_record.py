"""MessageRecord SQLAlchemy model."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String

from pycodeloop.core.models.base import Base


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
