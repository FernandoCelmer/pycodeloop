"""FileAccessRecord SQLAlchemy model."""

from __future__ import annotations

from sqlalchemy import Column, Float, Integer, String

from pycodeloop.store.models.base import Base


class FileAccessRecord(Base):
    __tablename__ = "file_access"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_key = Column(String, nullable=False, index=True)
    path = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    offset = Column(Integer, nullable=True)
    limit = Column(Integer, nullable=True)
    content_hash = Column(String, nullable=True)
    size = Column(Integer, nullable=True)
    accessed_at = Column(Float, nullable=False)
