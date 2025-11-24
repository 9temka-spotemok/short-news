"""
Helpers bridging Celery tasks with the competitors domain.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Awaitable, Callable, Optional
from uuid import UUID

import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_async import run_async_task
from app.core.database import AsyncSessionLocal
from app.domains.competitors import CompetitorFacade
from app.models import SourceType


@asynccontextmanager
async def _session_scope() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def _fetch_html(source_url: str) -> str:
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=10.0)) as client:
        response = await client.get(source_url)
        response.raise_for_status()
        return response.text


async def ingest_pricing_page(
    company_id: str,
    *,
    source_url: str,
    html: Optional[str] = None,
    source_type: SourceType = SourceType.NEWS_SITE,
) -> dict:
    async with _session_scope() as session:
        facade = CompetitorFacade(session)
        payload = html or await _fetch_html(source_url)
        event = await facade.ingest_pricing_page(
            company_id=company_id,
            source_url=source_url,
            html=payload,
            source_type=source_type,
        )
        return {
            "event_id": str(event.id),
            "company_id": str(event.company_id),
            "status": event.processing_status.value
            if hasattr(event.processing_status, "value")
            else event.processing_status,
        }


async def recompute_change_event(event_id: str) -> dict:
    async with _session_scope() as session:
        facade = CompetitorFacade(session)
        event = await facade.recompute_change_event(UUID(event_id))
        return {
            "event_id": str(event.id),
            "status": event.processing_status.value
            if hasattr(event.processing_status, "value")
            else event.processing_status,
        }


async def list_change_events(
    company_id: str,
    *,
    limit: int = 20,
) -> dict:
    async with _session_scope() as session:
        facade = CompetitorFacade(session)
        events = await facade.list_change_events(
            UUID(company_id),
            limit=limit,
        )
        return {
            "company_id": company_id,
            "events": [
                {
                    "id": str(event.id),
                    "summary": event.change_summary,
                    "detected_at": event.detected_at.isoformat()
                    if hasattr(event, "detected_at") and event.detected_at
                    else None,
                    "status": event.processing_status.value
                    if hasattr(event.processing_status, "value")
                    else event.processing_status,
                }
                for event in events
            ],
        }


def run_in_loop(factory: Callable[[], Awaitable[dict]]) -> dict:
    return run_async_task(factory())





