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
) -> str:
    service = CompetitorIngestionDomainService(session)
    event = await service.ingest_pricing_page(
        company_id=company.id,
        source_url="https://example.com/pricing",
        html=SAMPLE_HTML,
        source_type=SourceType.NEWS_SITE,
    )
    return str(event.id)


@pytest.mark.asyncio
async def test_list_change_events_endpoint(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    company = await _create_company(async_session, "Competify")
    await _ingest_pricing_change(async_session, company)

    response = await async_client.get(
        f"/api/v1/competitors/changes/{company.id}",
        params={"limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    event = payload["events"][0]
    assert event["company_id"] == str(company.id)
    assert event["change_summary"]
    assert event["processing_status"] in {"success", "skipped"}


@pytest.mark.asyncio
async def test_recompute_change_event_endpoint(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    company = await _create_company(async_session, "PriceWatch")
    event_id = await _ingest_pricing_change(async_session, company)

    response = await async_client.post(
        f"/api/v1/competitors/changes/{event_id}/recompute",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == event_id
    assert payload["processing_status"] in {"success", "skipped"}




