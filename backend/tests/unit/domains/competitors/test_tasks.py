from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.competitors.tasks import (
    ingest_pricing_page,
    list_change_events,
    recompute_change_event,
)
from app.models import Company, CompetitorChangeEvent
from app.models.news import SourceType

SAMPLE_HTML = """
<div class="pricing-card">
    <h3>Starter</h3>
    <div class="price">$29 per month</div>
    <ul class="features">
        <li>100 tracked prompts</li>
        <li>Email alerts</li>
    </ul>
</div>
"""


async def _create_company(session: AsyncSession, *, name: str) -> Company:
    company = Company(name=name, website="https://example.com")
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


@pytest.mark.asyncio
async def test_ingest_pricing_page_creates_change_event(async_session: AsyncSession) -> None:
    company = await _create_company(async_session, name="Competify")

    result = await ingest_pricing_page(
        str(company.id),
        source_url="https://example.com/pricing",
        html=SAMPLE_HTML,
        source_type=SourceType.NEWS_SITE,
    )

    assert result["status"] == "success"
    event_id = UUID(result["event_id"])

    stored_event = await async_session.get(CompetitorChangeEvent, event_id)
    assert stored_event is not None
    assert stored_event.company_id == company.id
    assert stored_event.change_summary


@pytest.mark.asyncio
async def test_list_and_recompute_change_events(async_session: AsyncSession) -> None:
    company = await _create_company(async_session, name="PriceWatch")

    ingestion = await ingest_pricing_page(
        str(company.id),
        source_url="https://pricewatch.io/pricing",
        html=SAMPLE_HTML,
        source_type=SourceType.NEWS_SITE,
    )
    event_id = ingestion["event_id"]

    listing = await list_change_events(str(company.id), limit=5)
    assert listing["status"] == "success"
    assert listing["company_id"] == str(company.id)
    assert listing["events"]
    assert listing["events"][0]["id"] == event_id

    recomputed = await recompute_change_event(event_id)
    assert recomputed["status"] == "success"
    assert recomputed["event_id"] == event_id




