"""
PostgreSQL Database Engine

This module provides PostgreSQL-specific database operations using asyncpg driver.

For database initialization (creating tables), run the setup script:
  uv run python -m app.database.postgres.scripts.init_db
"""

from app.database.postgres.engine import (
    async_engine,
    AsyncSessionLocal,
    get_db,
    close_db,
)

__all__ = [
    "async_engine",
    "AsyncSessionLocal",
    "get_db",
    "close_db",
]

