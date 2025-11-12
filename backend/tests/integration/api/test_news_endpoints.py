from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from uuid import uuid4

from app.models import Company, NewsItem
from app.models.news import NewsCategory, SourceType


async def _create_company(session: AsyncSession, name: str) -> Company:
    unique_suffix = uuid4().hex[:8]
    company = Company(name=f"{name}-{unique_suffix}", website=f"https://example.com/{unique_suffix}")
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


async def _create_news(
    session: AsyncSession,
    *,
    company: Company,
    title: str = "Breaking AI Update",
    category: NewsCategory = NewsCategory.PRODUCT_UPDATE,
    source_type: SourceType = SourceType.BLOG,
) -> NewsItem:
    news = NewsItem(
        title=title,
        summary="Initial summary",
        content="Some detailed content about AI.",
        source_url=f"https://example.com/{title.replace(' ', '-').lower()}",
        source_type=source_type,
        category=category,
        company_id=company.id,
        published_at=datetime.now(timezone.utc),
    )
    session.add(news)
    await session.commit()
    await session.refresh(news)
    return news


@pytest.mark.asyncio
async def test_create_news_endpoint(async_client: AsyncClient, async_session: AsyncSession) -> None:
    company = await _create_company(async_session, "OpenAI")
    company_id = str(company.id)

    payload = {
        "title": "New Product Launch",
        "summary": "Short summary",
        "content": "Detailed content for the new product launch.",
        "source_url": "https://example.com/new-product",
        "source_type": SourceType.BLOG.value,
        "category": NewsCategory.PRODUCT_UPDATE.value,
        "company_id": company_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }

    response = await async_client.post("/api/v1/news/", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == payload["title"]
    assert body["company"]["id"] == company_id


@pytest.mark.asyncio
async def test_get_news_filters(async_client: AsyncClient, async_session: AsyncSession) -> None:
    company_a = await _create_company(async_session, "OpenAI")
    company_b = await _create_company(async_session, "Anthropic")
    company_a_id = str(company_a.id)

    await _create_news(
        async_session,
        company=company_a,
        title="Pricing Update",
        category=NewsCategory.PRICING_CHANGE,
        source_type=SourceType.BLOG,
    )
    await _create_news(
        async_session,
        company=company_b,
        title="Tech Update",
        category=NewsCategory.TECHNICAL_UPDATE,
        source_type=SourceType.TWITTER,
    )

    response = await async_client.get(
        "/api/v1/news",
        params={
            "category": NewsCategory.PRICING_CHANGE.value,
            "company_ids": company_a_id,
            "limit": 10,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Pricing Update"


@pytest.mark.asyncio
async def test_news_statistics(async_client: AsyncClient, async_session: AsyncSession) -> None:
    company = await _create_company(async_session, "OpenAI")
    company_id = str(company.id)
    await _create_news(async_session, company=company, title="Stats News")

    response = await async_client.get("/api/v1/news/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] >= 1


@pytest.mark.asyncio
async def test_update_and_delete_news(async_client: AsyncClient, async_session: AsyncSession) -> None:
    company = await _create_company(async_session, "OpenAI")
    news = await _create_news(async_session, company=company)
    news_id = str(news.id)

    update_payload = {"summary": "Updated summary"}
    response = await async_client.put(
        f"/api/v1/news/{news_id}",
        json=update_payload,
    )
    assert response.status_code == 200
    assert response.json()["summary"] == "Updated summary"

    response = await async_client.delete(f"/api/v1/news/{news_id}")
    assert response.status_code == 204

    check = await async_client.get(f"/api/v1/news/{news_id}")
    assert check.status_code == 404



