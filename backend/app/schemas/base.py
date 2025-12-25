"""
Base Database Schema Components

This module contains only the base classes and mixins for database models:
- Base: Declarative base for all SQLAlchemy models
- TimestampMixin: Mixin for automatic timestamp columns

Database engine and session management is in app.database.postgres.engine
"""

from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models"""

    pass


class TimestampMixin:
    """Mixin for automatic created_at and updated_at timestamps"""

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
