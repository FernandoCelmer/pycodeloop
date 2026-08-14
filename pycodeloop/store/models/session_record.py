"""SessionRecord SQLAlchemy model."""

from __future__ import annotations

from sqlalchemy import Column, Float, Integer, String

from pycodeloop.store.models.base import Base


class SessionRecord(Base):
    __tablename__ = "sessions"

    key = Column(String, primary_key=True)
    system_prompt = Column(String, nullable=False)
    cwd = Column(String, nullable=False)
    updated_at = Column(Float, nullable=False)
    message_count = Column(Integer, nullable=False)
