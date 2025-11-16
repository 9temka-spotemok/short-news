from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsPeriod
from app.services.analytics_service import AnalyticsService
from tests.utils.analytics_builders import (
    create_company,
    create_news_item,
    create_change_event,
)


@pytest.mark.asyncio
async def test_compute_snapshot_for_period(async_session: AsyncSession) -> None:
    company = await create_company(async_session, name="AnalyticsCo")
    service = AnalyticsService(async_session)

    period_start = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=1)
    news_time = period_start + timedelta(hours=6)
    await create_news_item(async_session, company_id=company.id, title="Launch", published_at=news_time)
    await create_change_event(
        async_session,
        company_id=company.id,
        detected_at=period_start + timedelta(hours=8),
    )
    await async_session.commit()

    snapshot = await service.compute_snapshot_for_period(
        company.id,
        period_start,
        AnalyticsPeriod.DAILY,
    )

    assert snapshot.company_id == company.id
    assert snapshot.period == AnalyticsPeriod.DAILY
    assert snapshot.news_total == 1
    assert snapshot.pricing_changes >= 0
    assert snapshot.impact_score >= 0

    await async_session.refresh(snapshot)
    assert snapshot.components, "impact components should be persisted"

