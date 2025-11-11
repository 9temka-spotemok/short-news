from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsPeriod
from tests.utils.analytics_builders import create_company, create_snapshot


@pytest.mark.asyncio
async def test_get_latest_snapshot(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    company = await create_company(async_session, name="Analytics Test Co")
    period_start = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=1)
    await create_snapshot(async_session, company_id=company.id, period_start=period_start)

    response = await async_client.get(
        f"/api/v2/analytics/companies/{company.id}/impact/latest",
        params={"period": AnalyticsPeriod.DAILY.value},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_id"] == str(company.id)
    assert payload["period"] == AnalyticsPeriod.DAILY.value
    assert payload["impact_score"] == pytest.approx(4.2)
    assert payload["components"], "impact components should be serialized"


@pytest.mark.asyncio
async def test_get_snapshot_series(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    company = await create_company(async_session, name="Series Co")
    anchor = datetime.now(timezone.utc).replace(microsecond=0)
    await create_snapshot(async_session, company_id=company.id, period_start=anchor - timedelta(days=3))
    await create_snapshot(async_session, company_id=company.id, period_start=anchor - timedelta(days=2))

    response = await async_client.get(
        f"/api/v2/analytics/companies/{company.id}/snapshots",
        params={"period": AnalyticsPeriod.DAILY.value, "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_id"] == str(company.id)
    assert payload["period"] == AnalyticsPeriod.DAILY.value
    assert len(payload["snapshots"]) == 2

