from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.news.repositories.news_repository import (
    NewsFilters,
    NewsRepository,
)
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
async def test_fetch_by_url_returns_item(async_session: AsyncSession) -> None:
    repo = NewsRepository(async_session)
    company = await _create_company(async_session, "OpenAI")
    news = await _create_news(
        async_session,
        company=company,
        title="Launch GPT-X",
        category=NewsCategory.PRODUCT_UPDATE,
        source_type=SourceType.BLOG,
        published_at=_utc_now(),
    )

    fetched = await repo.fetch_by_url(news.source_url)

    assert fetched is not None
    assert fetched.id == news.id
    assert fetched.company is not None
    assert fetched.company.id == company.id


@pytest.mark.asyncio
async def test_list_news_applies_filters(async_session: AsyncSession) -> None:
    repo = NewsRepository(async_session)
    company_a = await _create_company(async_session, "OpenAI")
    company_b = await _create_company(async_session, "Anthropic")
    await _create_news(
        async_session,
        company=company_a,
        title="High priority pricing change",
        category=NewsCategory.PRICING_CHANGE,
        source_type=SourceType.BLOG,
        published_at=_utc_now(),
        priority=0.9,
    )
    await _create_news(
        async_session,
        company=company_b,
        title="Technical update",
        category=NewsCategory.TECHNICAL_UPDATE,
        source_type=SourceType.TWITTER,
        published_at=_utc_now(),
        priority=0.4,
    )

    filters = NewsFilters(
        category=NewsCategory.PRICING_CHANGE,
        company_ids=[str(company_a.id)],
        min_priority=0.8,
        limit=10,
        offset=0,
    )

    items, total = await repo.list_news(filters)

    assert total == 1
    assert len(items) == 1
    assert items[0].title.startswith("High priority")


@pytest.mark.asyncio
async def test_count_news_with_filters(async_session: AsyncSession) -> None:
    repo = NewsRepository(async_session)
    company = await _create_company(async_session, "OpenAI")
    recent = _utc_now()
    old = _utc_now() - timedelta(days=3)

    await _create_news(
        async_session,
        company=company,
        title="Recent high priority",
        category=NewsCategory.PRODUCT_UPDATE,
        source_type=SourceType.BLOG,
        published_at=recent,
        priority=0.95,
    )
    await _create_news(
        async_session,
        company=company,
        title="Older low priority",
        category=NewsCategory.PRODUCT_UPDATE,
        source_type=SourceType.BLOG,
        published_at=old,
        priority=0.3,
    )

    filters = NewsFilters(
        company_id=str(company.id),
        min_priority=0.8,
    )

    count = await repo.count_news(filters)

    assert count == 1


@pytest.mark.asyncio
async def test_fetch_recent_respects_cutoff(async_session: AsyncSession) -> None:
    repo = NewsRepository(async_session)
    company = await _create_company(async_session, "OpenAI")
    await _create_news(
        async_session,
        company=company,
        title="Recent item",
        category=NewsCategory.PRODUCT_UPDATE,
        source_type=SourceType.BLOG,
        published_at=_utc_now() - timedelta(hours=1),
    )
    await _create_news(
        async_session,
        company=company,
        title="Old item",
        category=NewsCategory.PRODUCT_UPDATE,
        source_type=SourceType.BLOG,
        published_at=_utc_now() - timedelta(hours=30),
    )

    items = await repo.fetch_recent(hours=24, limit=5)

    assert len(items) == 1
    assert items[0].title == "Recent item"


@pytest.mark.asyncio
async def test_aggregate_statistics_returns_counts(async_session: AsyncSession) -> None:
    repo = NewsRepository(async_session)
    company = await _create_company(async_session, "OpenAI")
    now = _utc_now()
    await _create_news(
        async_session,
        company=company,
        title="Recent high priority",
        category=NewsCategory.PRODUCT_UPDATE,
        source_type=SourceType.BLOG,
        published_at=now,
        priority=0.9,
    )
    await _create_news(
        async_session,
        company=None,
        title="Older news",
        category=NewsCategory.TECHNICAL_UPDATE,
        source_type=SourceType.TWITTER,
        published_at=now - timedelta(days=2),
        priority=0.2,
    )

    stats = await repo.aggregate_statistics()

    assert stats.total_count == 2
    assert stats.recent_count == 1
    assert stats.high_priority_count == 1
    assert stats.category_counts.get(NewsCategory.PRODUCT_UPDATE.value) == 1
    assert stats.category_counts.get(NewsCategory.TECHNICAL_UPDATE.value) == 1
    assert stats.source_counts.get(SourceType.BLOG.value) == 1
    assert stats.source_counts.get(SourceType.TWITTER.value) == 1


@pytest.mark.asyncio
async def test_aggregate_statistics_for_companies_filters(async_session: AsyncSession) -> None:
    repo = NewsRepository(async_session)
    company_a = await _create_company(async_session, "OpenAI")
    company_b = await _create_company(async_session, "Anthropic")
    now = _utc_now()
    await _create_news(
        async_session,
        company=company_a,
        title="OpenAI update",
        category=NewsCategory.PRODUCT_UPDATE,
        source_type=SourceType.BLOG,
        published_at=now,
        priority=0.9,
    )
    await _create_news(
        async_session,
        company=company_b,
        title="Anthropic update",
        category=NewsCategory.PRICING_CHANGE,
        source_type=SourceType.BLOG,
        published_at=now,
        priority=0.5,
    )

    stats = await repo.aggregate_statistics_for_companies([str(company_a.id)])

    assert stats.total_count == 1
    assert stats.category_counts == {NewsCategory.PRODUCT_UPDATE.value: 1}




