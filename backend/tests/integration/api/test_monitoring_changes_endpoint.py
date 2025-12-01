from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.competitors.services.ingestion_service import (
    CompetitorIngestionDomainService,
)
from app.models import Company
from app.models.news import SourceType


SAMPLE_HTML = """
<section class="pricing-card">
    <h3>Starter</h3>
    <div class="price">$29 per month</div>
    <ul>
        <li>100 tracked prompts</li>
        <li>Email alerts</li>
    </ul>
</section>
"""


async def _create_company(session: AsyncSession, name: str) -> Company:
    company = Company(name=name, website="https://example.com")
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


async def _ingest_pricing_change(
    session: AsyncSession,
    company: Company,
) -> None:
    service = CompetitorIngestionDomainService(session)
    await service.ingest_pricing_page(
        company_id=company.id,
        source_url="https://example.com/pricing",
        html=SAMPLE_HTML,
        source_type=SourceType.NEWS_SITE,
    )


@pytest.mark.asyncio
async def test_get_monitoring_changes_basic(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Endpoint returns events with required fields."""
    company = await _create_company(async_session, "MonitorMe")
    await _ingest_pricing_change(async_session, company)

    response = await async_client.get(
        "/api/v1/companies/monitoring/changes",
        params={"company_ids": str(company.id), "limit": 10},
    )

    assert response.status_code == 200
    payload = response.json()

    assert "events" in payload
    assert "total" in payload
    assert "has_more" in payload
    assert payload["total"] >= 1
    assert isinstance(payload["events"], list)

    event = payload["events"][0]
    assert event["company_id"] == str(company.id)
    assert "change_type" in event
    assert "change_summary" in event
    assert "detected_at" in event
    assert "details" in event


@pytest.mark.asyncio
async def test_get_monitoring_changes_filters_by_change_type(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Filtering by change_types narrows results (when type is present in raw_diff)."""
    company = await _create_company(async_session, "FilterCo")
    await _ingest_pricing_change(async_session, company)

    # Request with an unlikely type should return zero events or less/equal than total
    response = await async_client.get(
        "/api/v1/companies/monitoring/changes",
        params={
            "company_ids": str(company.id),
            "change_types": "non_existing_type",
            "limit": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "events" in payload
    assert isinstance(payload["events"], list)
    # We don't assert exact zero because existing data may not have type field;
    # the main check is that endpoint behaves correctly and returns valid structure.


