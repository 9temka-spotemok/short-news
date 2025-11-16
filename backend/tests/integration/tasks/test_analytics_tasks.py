from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.celery_app import celery_app
from app.models.analytics import AnalyticsPeriod
from app.services.analytics_service import AnalyticsService
from app.tasks import analytics as analytics_tasks


@pytest.mark.asyncio
async def test_recompute_company_analytics_task(
    async_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)
    monkeypatch.setattr(analytics_tasks, "AsyncSessionLocal", async_session_factory)

    call_args = {}

    async def fake_refresh(self, company_id: UUID, period: AnalyticsPeriod, lookback: int):
        call_args["company_id"] = company_id
        call_args["period"] = period
        call_args["lookback"] = lookback
        return ["snapshot"]

    monkeypatch.setattr(AnalyticsService, "refresh_company_snapshots", fake_refresh)

    company_id = uuid4()
    result = analytics_tasks.recompute_company_analytics.apply(
        args=(str(company_id), AnalyticsPeriod.DAILY.value, 5)
    ).get()

    assert result["status"] == "success"
    assert result["snapshots_recomputed"] == 1
    assert call_args["company_id"] == company_id
    assert call_args["period"] == AnalyticsPeriod.DAILY
    assert call_args["lookback"] == 5


@pytest.mark.asyncio
async def test_recompute_all_analytics_task(
    async_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)
    monkeypatch.setattr(analytics_tasks, "AsyncSessionLocal", async_session_factory)

    company_ids = [uuid4(), uuid4()]
    refresh_calls = []

    async def fake_load_company_ids(session):
        return company_ids

    async def fake_refresh(self, company_id: UUID, period: AnalyticsPeriod, lookback: int):
        refresh_calls.append((company_id, period, lookback))
        return ["snapshot"]

    monkeypatch.setattr(analytics_tasks, "_load_company_ids", fake_load_company_ids)
    monkeypatch.setattr(AnalyticsService, "refresh_company_snapshots", fake_refresh)

    result = analytics_tasks.recompute_all_analytics.apply(
        args=(AnalyticsPeriod.WEEKLY.value, 10)
    ).get()

    assert result["status"] == "success"
    assert result["companies_processed"] == len(company_ids)
    assert result["snapshots_recomputed"] == len(company_ids)
    assert refresh_calls and len(refresh_calls) == len(company_ids)
    for (company_id, period, lookback) in refresh_calls:
        assert company_id in company_ids
        assert period == AnalyticsPeriod.WEEKLY
        assert lookback == 10


@pytest.mark.asyncio
async def test_sync_company_knowledge_graph_task(
    async_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)
    monkeypatch.setattr(analytics_tasks, "AsyncSessionLocal", async_session_factory)

    call_args = {}

    async def fake_sync(
        self,
        company_id: UUID,
        period_start: datetime,
        period: AnalyticsPeriod,
    ):
        call_args["company_id"] = company_id
        call_args["period_start"] = period_start
        call_args["period"] = period
        return 5

    monkeypatch.setattr(AnalyticsService, "sync_knowledge_graph", fake_sync)

    company_id = uuid4()
    period_start = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=1)

    result = analytics_tasks.sync_company_knowledge_graph.apply(
        args=(
            str(company_id),
            period_start.isoformat(),
            AnalyticsPeriod.DAILY.value,
        )
    ).get()

    assert result["status"] == "success"
    assert result["edges_created"] == 5
    assert call_args["company_id"] == company_id
    assert call_args["period"] == AnalyticsPeriod.DAILY
    assert call_args["period_start"].replace(tzinfo=timezone.utc) == period_start.replace(
        tzinfo=timezone.utc
    )




