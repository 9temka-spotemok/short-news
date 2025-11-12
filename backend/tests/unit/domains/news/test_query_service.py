from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.news.services.query_service import NewsQueryService
from app.models import Company, NewsItem
from app.models.news import NewsCategory, SourceType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def _create_company(session: AsyncSession, name: str) -> Company:
    company = Company(name=name)
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


async def _create_news(
    session: AsyncSession,
    *,
    company: Company | None,
    title: str,
    category: NewsCategory,
    source_type: SourceType,
    published_at: datetime,
    priority: float = 0.5,
) -> NewsItem:
    news = NewsItem(
        title=title,
        summary=f"{title} summary",
        content=f"{title} content",
        source_url=f"https://example.com/{uuid4()}",
        source_type=source_type,
        company_id=str(company.id) if company else None,
        category=category,
        published_at=published_at.replace(tzinfo=None),
        priority_score=priority,
    )
    session.add(news)
    await session.commit()
    await session.refresh(news)
    return news


@pytest.mark.asyncio
async def test_list_news_returns_items(async_session: AsyncSession) -> None:
    service = NewsQueryService(async_session)
    company = await _create_company(async_session, "OpenAI")
    await _create_news(
        async_session,
        company=company,
        title="Pricing update",
        category=NewsCategory.PRICING_CHANGE,
        source_type=SourceType.BLOG,
        published_at=_utc_now(),
        priority=0.9,
    )

    items, total = await service.list_news(
        category=NewsCategory.PRICING_CHANGE,
        company_ids=[str(company.id)],
        min_priority=0.8,
    )

    assert total == 1
    assert len(items) == 1
    assert items[0].title == "Pricing update"


@pytest.mark.asyncio
async def test_fetch_recent_filters_by_time(async_session: AsyncSession) -> None:
    service = NewsQueryService(async_session)
    company = await _create_company(async_session, "Anthropic")
    await _create_news(
        async_session,
        company=company,
        title="Recent technical update",
        category=NewsCategory.TECHNICAL_UPDATE,
        source_type=SourceType.BLOG,
        published_at=_utc_now() - timedelta(hours=2),
    )
    await _create_news(
        async_session,
        company=company,
        title="Old news",
        category=NewsCategory.TECHNICAL_UPDATE,
        source_type=SourceType.BLOG,
        published_at=_utc_now() - timedelta(days=2),
    )

    items = await service.fetch_recent(hours=24, limit=5)

    assert len(items) == 1
    assert items[0].title == "Recent technical update"


@pytest.mark.asyncio
async def test_get_statistics_aggregates_fields(async_session: AsyncSession) -> None:
    service = NewsQueryService(async_session)
    company = await _create_company(async_session, "OpenAI")
    now = _utc_now()
    await _create_news(
        async_session,
        company=company,
        title="High priority news",
        category=NewsCategory.PRODUCT_UPDATE,
        source_type=SourceType.BLOG,
        published_at=now,
        priority=0.85,
    )
    await _create_news(
        async_session,
        company=None,
        title="Other news",
        category=NewsCategory.TECHNICAL_UPDATE,
        source_type=SourceType.TWITTER,
        published_at=now - timedelta(days=3),
        priority=0.1,
    )

    stats = await service.get_statistics()

    assert stats.total_count == 2
    assert stats.recent_count == 1
    assert stats.high_priority_count == 1
    assert stats.category_counts.get(NewsCategory.PRODUCT_UPDATE.value) == 1
    assert stats.source_counts.get(SourceType.BLOG.value) == 1




