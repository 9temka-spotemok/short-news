"""
Shared async SQLAlchemy engine/session factory for Celery workers.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

celery_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
)

CelerySessionLocal = async_sessionmaker(
    celery_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


