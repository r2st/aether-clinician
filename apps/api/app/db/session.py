"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _make_engine() -> AsyncEngine:
    url = settings.database_url
    kwargs: dict = {"echo": False, "future": True}
    if url.startswith("postgresql"):
        kwargs.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
        )
    return create_async_engine(url, **kwargs)


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(), expire_on_commit=False, autoflush=False
        )
    return _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped session."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
