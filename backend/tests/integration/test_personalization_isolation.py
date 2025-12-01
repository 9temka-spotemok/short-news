"""
Integration tests for data isolation between users.

Tests that user A cannot see user B's data:
- Companies
- News items
- Reports
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, NewsItem, Report, User
from app.models.news import NewsCategory, ReportStatus, SourceType


@pytest.mark.asyncio
async def test_user_a_cannot_see_user_b_companies(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Test that user A cannot see user B's companies."""
    # Create two users
    user_a = User(email="user_a@example.com", hashed_password="hashed")
    user_b = User(email="user_b@example.com", hashed_password="hashed")
    async_session.add(user_a)
    async_session.add(user_b)
    await async_session.commit()
    await async_session.refresh(user_a)
    await async_session.refresh(user_b)

    # Create companies for each user
    company_a = Company(
        name="User A Company",
        website="https://user-a.com",
        user_id=user_a.id,
    )
    company_b = Company(
        name="User B Company",
        website="https://user-b.com",
        user_id=user_b.id,
    )
    async_session.add(company_a)
    async_session.add(company_b)
    await async_session.commit()
    await async_session.refresh(company_a)
    await async_session.refresh(company_b)

    # Get auth token for user A
    # Note: This assumes you have an auth endpoint. Adjust as needed.
    # For now, we'll test the access control directly
    from app.core.access_control import check_company_access

    # User A can access their own company
    result_a = await check_company_access(company_a.id, user_a, async_session)
    assert result_a is not None
    assert result_a.id == company_a.id

    # User A cannot access user B's company
    result_b = await check_company_access(company_b.id, user_a, async_session)
    assert result_b is None


@pytest.mark.asyncio
async def test_user_a_cannot_see_user_b_news(
    async_session: AsyncSession,
) -> None:
    """Test that user A cannot see user B's news."""
    # Create two users
    user_a = User(email="user_a@example.com", hashed_password="hashed")
    user_b = User(email="user_b@example.com", hashed_password="hashed")
    async_session.add(user_a)
    async_session.add(user_b)
    await async_session.commit()
    await async_session.refresh(user_a)
    await async_session.refresh(user_b)

    # Create companies for each user
    company_a = Company(
        name="User A Company",
        website="https://user-a.com",
        user_id=user_a.id,
    )
    company_b = Company(
        name="User B Company",
        website="https://user-b.com",
        user_id=user_b.id,
    )
    async_session.add(company_a)
    async_session.add(company_b)
    await async_session.commit()
    await async_session.refresh(company_a)
    await async_session.refresh(company_b)

    # Create news for each company
    news_a = NewsItem(
        title="User A News",
        summary="Summary A",
        content="Content A",
        source_url="https://user-a.com/news",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=company_a.id,
        published_at=datetime.now(timezone.utc),
    )
    news_b = NewsItem(
        title="User B News",
        summary="Summary B",
        content="Content B",
        source_url="https://user-b.com/news",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=company_b.id,
        published_at=datetime.now(timezone.utc),
    )
    async_session.add(news_a)
    async_session.add(news_b)
    await async_session.commit()
    await async_session.refresh(news_a)
    await async_session.refresh(news_b)

    from app.core.access_control import check_news_access

    # User A can access their own news
    result_a = await check_news_access(news_a.id, user_a, async_session)
    assert result_a is not None
    assert result_a.id == news_a.id

    # User A cannot access user B's news
    result_b = await check_news_access(news_b.id, user_a, async_session)
    assert result_b is None


@pytest.mark.asyncio
async def test_user_a_cannot_see_user_b_reports(
    async_session: AsyncSession,
) -> None:
    """Test that user A cannot see user B's reports."""
    # Create two users
    user_a = User(email="user_a@example.com", hashed_password="hashed")
    user_b = User(email="user_b@example.com", hashed_password="hashed")
    async_session.add(user_a)
    async_session.add(user_b)
    await async_session.commit()
    await async_session.refresh(user_a)
    await async_session.refresh(user_b)

    # Create companies for each user
    company_a = Company(
        name="User A Company",
        website="https://user-a.com",
        user_id=user_a.id,
    )
    company_b = Company(
        name="User B Company",
        website="https://user-b.com",
        user_id=user_b.id,
    )
    async_session.add(company_a)
    async_session.add(company_b)
    await async_session.commit()
    await async_session.refresh(company_a)
    await async_session.refresh(company_b)

    # Create reports for each user
    report_a = Report(
        user_id=user_a.id,
        query="user-a.com",
        status=ReportStatus.READY,
        company_id=company_a.id,
    )
    report_b = Report(
        user_id=user_b.id,
        query="user-b.com",
        status=ReportStatus.READY,
        company_id=company_b.id,
    )
    async_session.add(report_a)
    async_session.add(report_b)
    await async_session.commit()
    await async_session.refresh(report_a)
    await async_session.refresh(report_b)

    from app.domains.reports.repositories.report_repository import ReportRepository

    repo = ReportRepository(async_session)

    # User A can access their own report
    result_a = await repo.get_by_id(report_a.id, user_id=user_a.id)
    assert result_a is not None
    assert result_a.id == report_a.id

    # User A cannot access user B's report
    result_b = await repo.get_by_id(report_b.id, user_id=user_a.id)
    assert result_b is None


@pytest.mark.asyncio
async def test_user_sees_all_own_companies(
    async_session: AsyncSession,
) -> None:
    """Test that user sees all their own companies."""
    # Create user
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create multiple companies for user
    companies = []
    for i in range(5):
        company = Company(
            name=f"Company {i}",
            website=f"https://company{i}.com",
            user_id=user.id,
        )
        async_session.add(company)
        companies.append(company)
    await async_session.commit()
    for company in companies:
        await async_session.refresh(company)

    from app.core.access_control import get_user_company_ids

    # Get all user's companies
    company_ids = await get_user_company_ids(user, async_session)

    assert len(company_ids) == 5
    for company in companies:
        assert company.id in company_ids


@pytest.mark.asyncio
async def test_user_sees_all_own_news(
    async_session: AsyncSession,
) -> None:
    """Test that user sees all news from their own companies."""
    # Create user
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create company for user
    company = Company(
        name="Test Company",
        website="https://test.com",
        user_id=user.id,
    )
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)

    # Create multiple news items for company
    news_items = []
    for i in range(5):
        news = NewsItem(
            title=f"News {i}",
            summary=f"Summary {i}",
            content=f"Content {i}",
            source_url=f"https://test.com/news{i}",
            source_type=SourceType.BLOG,
            category=NewsCategory.PRODUCT_UPDATE,
            company_id=company.id,
            published_at=datetime.now(timezone.utc),
        )
        async_session.add(news)
        news_items.append(news)
    await async_session.commit()
    for news in news_items:
        await async_session.refresh(news)

    from app.core.access_control import check_news_access

    # User can access all their news
    for news in news_items:
        result = await check_news_access(news.id, user, async_session)
        assert result is not None
        assert result.id == news.id





