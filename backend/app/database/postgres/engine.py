"""
PostgreSQL Database Engine and Session Management

This module handles all PostgreSQL-specific database operations:
- Database engine creation
- Session factory
- Connection lifecycle management
- FastAPI dependency injection
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from typing import AsyncGenerator
from app.core.config import settings


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


async def close_db():
    """
    Close database connections - for application shutdown
    
    This should be called when the application is shutting down to
    properly dispose of all database connections in the pool.
    """
    await async_engine.dispose()

