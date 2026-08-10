"""Shared SQLAlchemy declarative base for all pycodeloop models."""

from __future__ import annotations

from sqlalchemy.orm import declarative_base

Base = declarative_base()
