"""
Helpers for integrating Celery tasks with the news domain.

Provides async adapters that reuse the domain facade and NLP pipeline without
touching legacy global session factories from the task layer.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Awaitable, Callable
import threading
import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

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
    Execute async coroutine in a fresh loop.

    Celery tasks are synchronous by default; this helper allows us to keep the
    async implementation in the domain while providing a sync bridge.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())

    result_holder: dict[str, dict] = {}
    exception_holder: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result_holder["value"] = asyncio.run(coro_factory())
        except BaseException as exc:  # pragma: no cover - propagate to caller
            exception_holder["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if "error" in exception_holder:
        raise exception_holder["error"]

    return result_holder.get("value")

