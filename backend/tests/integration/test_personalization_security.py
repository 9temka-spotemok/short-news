"""
Security tests for personalization - protection against ID spoofing.

Tests that users cannot access other users' data by spoofing IDs:
- Companies
- News items
- Reports
- Competitor comparisons
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
async def test_cannot_access_other_user_company_by_id(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Test that user cannot access another user's company by ID spoofing."""
    # Create two users
    user_a = User(email="user_a@example.com", hashed_password="hashed")
    user_b = User(email="user_b@example.com", hashed_password="hashed")
    async_session.add(user_a)
    async_session.add(user_b)
    await async_session.commit()
    await async_session.refresh(user_a)
    await async_session.refresh(user_b)

    # Create company for user B
    company_b = Company(
        name="User B Company",
        website="https://user-b.com",
        user_id=user_b.id,
    )
    async_session.add(company_b)
    await async_session.commit()
    await async_session.refresh(company_b)

    from app.core.access_control import check_company_access

    # User A tries to access user B's company by ID
    result = await check_company_access(company_b.id, user_a, async_session)

    # Should return None (access denied)
    assert result is None


@pytest.mark.asyncio
async def test_cannot_access_other_user_news_by_id(
    async_session: AsyncSession,
) -> None:
    """Test that user cannot access another user's news by ID spoofing."""
    # Create two users
    user_a = User(email="user_a@example.com", hashed_password="hashed")
    user_b = User(email="user_b@example.com", hashed_password="hashed")
    async_session.add(user_a)
    async_session.add(user_b)
    await async_session.commit()
    await async_session.refresh(user_a)
    await async_session.refresh(user_b)

    # Create company for user B
    company_b = Company(
        name="User B Company",
        website="https://user-b.com",
        user_id=user_b.id,
    )
    async_session.add(company_b)
    await async_session.commit()
    await async_session.refresh(company_b)

    # Create news for user B's company
    news_b = NewsItem(
        title="User B News",
        summary="Summary",
        content="Content",
        source_url="https://user-b.com/news",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=company_b.id,
        published_at=datetime.now(timezone.utc),
    )
    async_session.add(news_b)
    await async_session.commit()
    await async_session.refresh(news_b)

    from app.core.access_control import check_news_access

    # User A tries to access user B's news by ID
    result = await check_news_access(news_b.id, user_a, async_session)

    # Should return None (access denied)
    assert result is None


@pytest.mark.asyncio
async def test_cannot_access_other_user_report_by_id(
    async_session: AsyncSession,
) -> None:
    """Test that user cannot access another user's report by ID spoofing."""
    # Create two users
    user_a = User(email="user_a@example.com", hashed_password="hashed")
    user_b = User(email="user_b@example.com", hashed_password="hashed")
    async_session.add(user_a)
    async_session.add(user_b)
    await async_session.commit()
    await async_session.refresh(user_a)
    await async_session.refresh(user_b)

    # Create company for user B
    company_b = Company(
        name="User B Company",
        website="https://user-b.com",
        user_id=user_b.id,
    )
    async_session.add(company_b)
    await async_session.commit()
    await async_session.refresh(company_b)

    # Create report for user B
    report_b = Report(
        user_id=user_b.id,
        query="user-b.com",
        status=ReportStatus.READY,
        company_id=company_b.id,
    )
    async_session.add(report_b)
    await async_session.commit()
    await async_session.refresh(report_b)

    from app.domains.reports.repositories.report_repository import ReportRepository

    repo = ReportRepository(async_session)

    # User A tries to access user B's report by ID
    result = await repo.get_by_id(report_b.id, user_id=user_a.id)

    # Should return None (access denied)
    assert result is None


@pytest.mark.asyncio
async def test_cannot_compare_other_user_companies(
    async_session: AsyncSession,
) -> None:
    """Test that user cannot compare other users' companies."""
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
    company_b1 = Company(
        name="User B Company 1",
        website="https://user-b1.com",
        user_id=user_b.id,
    )
    company_b2 = Company(
        name="User B Company 2",
        website="https://user-b2.com",
        user_id=user_b.id,
    )
    async_session.add(company_a)
    async_session.add(company_b1)
    async_session.add(company_b2)
    await async_session.commit()
    await async_session.refresh(company_a)
    await async_session.refresh(company_b1)
    await async_session.refresh(company_b2)

    from app.core.access_control import check_company_access

    # User A tries to compare their company with user B's companies
    # First check: user A's company - should work
    result_a = await check_company_access(company_a.id, user_a, async_session)
    assert result_a is not None

    # Second check: user B's company - should fail
    result_b1 = await check_company_access(company_b1.id, user_a, async_session)
    assert result_b1 is None

    result_b2 = await check_company_access(company_b2.id, user_a, async_session)
    assert result_b2 is None


@pytest.mark.asyncio
async def test_cannot_get_suggestions_for_other_user_company(
    async_session: AsyncSession,
) -> None:
    """Test that user cannot get competitor suggestions for another user's company."""
    # Create two users
    user_a = User(email="user_a@example.com", hashed_password="hashed")
    user_b = User(email="user_b@example.com", hashed_password="hashed")
    async_session.add(user_a)
    async_session.add(user_b)
    await async_session.commit()
    await async_session.refresh(user_a)
    await async_session.refresh(user_b)

    # Create company for user B
    company_b = Company(
        name="User B Company",
        website="https://user-b.com",
        user_id=user_b.id,
    )
    async_session.add(company_b)
    await async_session.commit()
    await async_session.refresh(company_b)

    from app.core.access_control import check_company_access

    # User A tries to get suggestions for user B's company
    result = await check_company_access(company_b.id, user_a, async_session)

    # Should return None (access denied)
    assert result is None


@pytest.mark.asyncio
async def test_cannot_access_company_with_invalid_id(
    async_session: AsyncSession,
) -> None:
    """Test that invalid company ID returns None."""
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    from app.core.access_control import check_company_access

    # Try with invalid UUID
    result = await check_company_access("invalid-uuid", user, async_session)
    assert result is None

    # Try with non-existent UUID
    fake_uuid = uuid4()
    result = await check_company_access(fake_uuid, user, async_session)
    assert result is None


@pytest.mark.asyncio
async def test_cannot_access_news_with_invalid_id(
    async_session: AsyncSession,
) -> None:
    """Test that invalid news ID returns None."""
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    from app.core.access_control import check_news_access

    # Try with invalid UUID
    result = await check_news_access("invalid-uuid", user, async_session)
    assert result is None

    # Try with non-existent UUID
    fake_uuid = uuid4()
    result = await check_news_access(fake_uuid, user, async_session)
    assert result is None





