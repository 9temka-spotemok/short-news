"""
Celery tasks for analytics calculations and knowledge graph synchronisation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from loguru import logger

from app.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models import AnalyticsPeriod, Company
from app.services.analytics_service import AnalyticsService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@celery_app.task(bind=True, ignore_result=False)
def recompute_company_analytics(self, company_id: str, period: str = AnalyticsPeriod.DAILY.value, lookback: int = 30):
    """
    Recompute analytics snapshots for a single company.
    """
    logger.info("Recomputing analytics for company %s (period=%s, lookback=%s)", company_id, period, lookback)

    try:
        result = asyncio.run(_recompute_company_analytics_async(UUID(company_id), AnalyticsPeriod(period), lookback))
        logger.info(
            "Analytics recompute finished for company %s (%s snapshots)",
            company_id,
            result["snapshots_recomputed"],
        )
        return result
    except Exception as exc:
        logger.error("Analytics recompute failed for company %s: %s", company_id, exc, exc_info=True)
        raise self.retry(exc=exc, countdown=120, max_retries=3)


async def _recompute_company_analytics_async(company_id: UUID, period: AnalyticsPeriod, lookback: int):
    async with AsyncSessionLocal() as session:
        service = AnalyticsService(session)
        snapshots = await service.refresh_company_snapshots(company_id=company_id, period=period, lookback=lookback)
        await session.commit()
        return {
            "status": "success",
            "company_id": str(company_id),
            "period": period.value,
            "snapshots_recomputed": len(snapshots),
        }


@celery_app.task(bind=True, ignore_result=False)
def recompute_all_analytics(self, period: str = AnalyticsPeriod.DAILY.value, lookback: int = 30):
    """
    Recompute analytics snapshots for all companies.
    """
    logger.info("Starting global analytics recompute (period=%s lookback=%s)", period, lookback)

    try:
        result = asyncio.run(_recompute_all_analytics_async(AnalyticsPeriod(period), lookback))
        logger.info(
            "Global analytics recompute complete (%s companies updated)",
            result["companies_processed"],
        )
        return result
    except Exception as exc:
        logger.error("Global analytics recompute failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=300, max_retries=2)


async def _recompute_all_analytics_async(period: AnalyticsPeriod, lookback: int):
    async with AsyncSessionLocal() as session:
        company_ids = await _load_company_ids(session)
        service = AnalyticsService(session)
        total_snapshots = 0

        for company_id in company_ids:
            snapshots = await service.refresh_company_snapshots(company_id=company_id, period=period, lookback=lookback)
            total_snapshots += len(snapshots)

        await session.commit()
        return {
            "status": "success",
            "companies_processed": len(company_ids),
            "snapshots_recomputed": total_snapshots,
        }


@celery_app.task(bind=True, ignore_result=False)
def sync_company_knowledge_graph(
    self,
    company_id: str,
    period_start_iso: str,
    period: str = AnalyticsPeriod.DAILY.value,
):
    """
    Derive knowledge graph edges for a company within a period.
    """
    logger.info(
        "Synchronising analytics graph for company %s (period=%s start=%s)",
        company_id,
        period,
        period_start_iso,
    )

    try:
        period_start = _parse_period_start(period_start_iso)
        result = asyncio.run(
            _sync_company_graph_async(
                UUID(company_id),
                AnalyticsPeriod(period),
                period_start,
            )
        )
        logger.info(
            "Graph sync complete for company %s (%s edges created)",
            company_id,
            result["edges_created"],
        )
        return result
    except Exception as exc:
        logger.error("Graph sync failed for company %s: %s", company_id, exc, exc_info=True)
        raise self.retry(exc=exc, countdown=180, max_retries=3)


async def _sync_company_graph_async(
    company_id: UUID,
    period: AnalyticsPeriod,
    period_start: datetime,
):
    async with AsyncSessionLocal() as session:
        service = AnalyticsService(session)
        created_edges = await service.sync_knowledge_graph(
            company_id=company_id,
            period_start=period_start,
            period=period,
        )
        await session.commit()
        return {
            "status": "success",
            "company_id": str(company_id),
            "period": period.value,
            "edges_created": created_edges,
        }


async def _load_company_ids(session: AsyncSession) -> List[UUID]:
    result = await session.execute(select(Company.id))
    return list(result.scalars().all())


def _parse_period_start(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    period_start = datetime.fromisoformat(value)
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=timezone.utc)
    return period_start


