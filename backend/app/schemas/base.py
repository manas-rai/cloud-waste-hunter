"""
Base Database Models with Async Session Management
"""

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    String,
    Boolean,
    JSON,
    Float,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase, declared_attr
from datetime import datetime, timezone
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""

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


# Convert sync DATABASE_URL to async
def get_async_database_url() -> str:
    """Convert PostgreSQL URL to asyncpg format"""
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        # Replace psycopg2 driver with asyncpg
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return url


# Async database engine
async_engine = create_async_engine(
    get_async_database_url(),
    echo=settings.DEBUG,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,  # Connection pool size
    max_overflow=20,  # Max connections beyond pool_size
    pool_recycle=3600,  # Recycle connections after 1 hour
)


# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting async database session with proper cleanup.
    
    This ensures:
    - Session is properly created
    - Transaction is committed on success
    - Transaction is rolled back on error
    - Session is always closed (no leaks)
    - Works with FastAPI's dependency injection
    
    Usage in endpoints:
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Model))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database (create tables) - for startup"""
    async with async_engine.begin() as conn:
        # Import all models to register them
        from app.schemas.detection import Detection
        from app.schemas.audit import AuditLog
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections - for shutdown"""
    await async_engine.dispose()
