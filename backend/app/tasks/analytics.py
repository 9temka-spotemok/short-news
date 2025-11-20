"""
Celery tasks for analytics calculations and knowledge graph synchronisation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from loguru import logger

from app.celery_app import celery_app
from app.core.celery_async import run_async_task
from app.core.database import AsyncSessionLocal
from app.instrumentation import TaskExecutionContext
from app.models import AnalyticsPeriod, Company
from app.domains.analytics import AnalyticsFacade
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_ANALYTICS_LABELS = {"queue": "analytics"}


@celery_app.task(bind=True, ignore_result=False)
def recompute_company_analytics(self, company_id: str, period: str = AnalyticsPeriod.DAILY.value, lookback: int = 30):
    """
    Recompute analytics snapshots for a single company.
    """
    analytics_period = AnalyticsPeriod(period)
    dedup_key = f"analytics:company:{company_id}:{analytics_period.value}:{lookback}"
    labels = {**_ANALYTICS_LABELS, "period": analytics_period.value}

    logger.info(
        "Recomputing analytics for company %s (period=%s, lookback=%s)",
        company_id,
        analytics_period.value,
        lookback,
    )

    with TaskExecutionContext(
        "recompute_company_analytics",
        dedup_key=dedup_key,
        labels=labels,
        duplicate_payload={
            "status": "duplicate",
            "reason": "already_processing_company_period",
            "company_id": company_id,
            "period": analytics_period.value,
        },
    ) as ctx:
        if not ctx.should_run:
            return ctx.result

        try:
            result = run_async_task(_recompute_company_analytics_async(
                UUID(company_id),
                analytics_period,
                lookback,
            ))
            logger.info(
                "Analytics recompute finished for company %s (%s snapshots)",
                company_id,
                result["snapshots_recomputed"],
            )
            return ctx.finish(result)
        except Exception as exc:
            logger.error("Analytics recompute failed for company %s: %s", company_id, exc, exc_info=True)
            raise self.retry(exc=exc, countdown=120, max_retries=3)


async def _recompute_company_analytics_async(company_id: UUID, period: AnalyticsPeriod, lookback: int):
    async with AsyncSessionLocal() as session:
        facade = AnalyticsFacade(session)
        snapshots = await facade.refresh_company_snapshots(company_id=company_id, period=period, lookback=lookback)
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
    analytics_period = AnalyticsPeriod(period)
    dedup_key = f"analytics:global:{analytics_period.value}:{lookback}"
    labels = {**_ANALYTICS_LABELS, "period": analytics_period.value}

    logger.info("Starting global analytics recompute (period=%s lookback=%s)", analytics_period.value, lookback)

    with TaskExecutionContext(
        "recompute_all_analytics",
        dedup_key=dedup_key,
        labels=labels,
        duplicate_payload={
            "status": "duplicate",
            "reason": "global_recompute_in_progress",
            "period": analytics_period.value,
        },
    ) as ctx:
        if not ctx.should_run:
            return ctx.result

        try:
            result = run_async_task(_recompute_all_analytics_async(
                analytics_period,
                lookback,
            ))
            logger.info(
                "Global analytics recompute complete (%s companies updated)",
                result["companies_processed"],
            )
            return ctx.finish(result)
        except Exception as exc:
            logger.error("Global analytics recompute failed: %s", exc, exc_info=True)
            raise self.retry(exc=exc, countdown=300, max_retries=2)


async def _recompute_all_analytics_async(period: AnalyticsPeriod, lookback: int):
    async with AsyncSessionLocal() as session:
        company_ids = await _load_company_ids(session)
        facade = AnalyticsFacade(session)
        total_snapshots = 0

        for company_id in company_ids:
            snapshots = await facade.refresh_company_snapshots(company_id=company_id, period=period, lookback=lookback)
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
    analytics_period = AnalyticsPeriod(period)
    labels = {**_ANALYTICS_LABELS, "period": analytics_period.value}
    dedup_key = f"analytics:graph:{company_id}:{analytics_period.value}:{period_start_iso}"

    logger.info(
        "Synchronising analytics graph for company %s (period=%s start=%s)",
        company_id,
        analytics_period.value,
        period_start_iso,
    )

    with TaskExecutionContext(
        "sync_company_knowledge_graph",
        dedup_key=dedup_key,
        labels=labels,
        duplicate_payload={
            "status": "duplicate",
            "reason": "graph_sync_in_progress",
            "company_id": company_id,
            "period": analytics_period.value,
            "period_start": period_start_iso,
        },
    ) as ctx:
        if not ctx.should_run:
            return ctx.result

        try:
            period_start = _parse_period_start(period_start_iso)
            result = run_async_task(_sync_company_graph_async(
                UUID(company_id),
                analytics_period,
                period_start,
            ))
            logger.info(
                "Graph sync complete for company %s (%s edges created)",
                company_id,
                result["edges_created"],
            )
            return ctx.finish(result)
        except Exception as exc:
            logger.error("Graph sync failed for company %s: %s", company_id, exc, exc_info=True)
            raise self.retry(exc=exc, countdown=180, max_retries=3)


async def _sync_company_graph_async(
    company_id: UUID,
    period: AnalyticsPeriod,
    period_start: datetime,
):
    async with AsyncSessionLocal() as session:
        facade = AnalyticsFacade(session)
        created_edges = await facade.sync_knowledge_graph(
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


