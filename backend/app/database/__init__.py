"""
Database Layer

This package handles database connection management:
- Database engine and session management
- Connection lifecycle (get_db, close_db)

Note: Database initialization (creating tables) is done via:
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

