"""
Helpers for integrating Celery tasks with the news domain.

Provides async adapters that reuse the domain facade and NLP pipeline without
touching legacy global session factories from the task layer.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_async import run_async_task
from app.core.database import AsyncSessionLocal
from app.domains.news import NewsFacade
from app.services.nlp_service import PIPELINE


@asynccontextmanager
async def _session_scope() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def classify_news(news_id: str | UUID) -> dict:
    news_uuid = UUID(str(news_id))
    async with _session_scope() as session:
        facade = NewsFacade(session)
        # ensure the news item exists through the facade before classification
        news = await facade.get_news_item(news_uuid)
        if not news:
            raise ValueError(f"News item {news_id} not found")
        return await PIPELINE.classify_news(session, str(news_uuid))


async def summarise_news(news_id: str | UUID, *, force: bool = False) -> dict:
    news_uuid = UUID(str(news_id))
    async with _session_scope() as session:
        facade = NewsFacade(session)
        news = await facade.get_news_item(news_uuid)
        if not news:
            raise ValueError(f"News item {news_id} not found")
        return await PIPELINE.summarise_news(session, str(news_uuid), force=force)


async def extract_keywords(news_id: str | UUID, *, limit: int = 8) -> dict:
    news_uuid = UUID(str(news_id))
    async with _session_scope() as session:
        facade = NewsFacade(session)
        news = await facade.get_news_item(news_uuid)
        if not news:
            raise ValueError(f"News item {news_id} not found")
        return await PIPELINE.extract_keywords(session, str(news_uuid), limit=limit)


def run_in_loop(coro_factory: Callable[[], Awaitable[dict]]) -> dict:
    """
    Execute async coroutine using the shared Celery event loop.
    """
    return run_async_task(coro_factory())

