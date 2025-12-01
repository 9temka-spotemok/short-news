"""
Unit tests for access control functions.

Tests for:
- check_company_access()
- check_news_access()
- get_user_company_ids()
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import (
    check_company_access,
    check_news_access,
    get_user_company_ids,
)
from app.models import Company, NewsItem, User
from app.models.news import NewsCategory, SourceType


@pytest.mark.asyncio
async def test_check_company_access_user_owns_company(
    async_session: AsyncSession,
) -> None:
    """Test that user can access their own company."""
    # Create user
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create company owned by user
    company = Company(
        name="Test Company",
        website="https://test.com",
        user_id=user.id,
    )
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)

    # Check access
    result = await check_company_access(company.id, user, async_session)

    assert result is not None
    assert result.id == company.id
    assert result.name == company.name


@pytest.mark.asyncio
async def test_check_company_access_user_does_not_own_company(
    async_session: AsyncSession,
) -> None:
    """Test that user cannot access another user's company."""
    # Create two users
    user1 = User(email="user1@example.com", hashed_password="hashed")
    user2 = User(email="user2@example.com", hashed_password="hashed")
    async_session.add(user1)
    async_session.add(user2)
    await async_session.commit()
    await async_session.refresh(user1)
    await async_session.refresh(user2)

    # Create company owned by user1
    company = Company(
        name="User1 Company",
        website="https://user1.com",
        user_id=user1.id,
    )
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)

    # User2 tries to access user1's company
    result = await check_company_access(company.id, user2, async_session)

    assert result is None


@pytest.mark.asyncio
async def test_check_company_access_global_company(
    async_session: AsyncSession,
) -> None:
    """Test that any user can access global company (user_id is None)."""
    # Create user
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create global company (user_id is None)
    company = Company(
        name="Global Company",
        website="https://global.com",
        user_id=None,
    )
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)

    # User can access global company
    result = await check_company_access(company.id, user, async_session)

    assert result is not None
    assert result.id == company.id


@pytest.mark.asyncio
async def test_check_company_access_anonymous_user(
    async_session: AsyncSession,
) -> None:
    """Test that anonymous user can only access global companies."""
    # Create user-owned company
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    company_owned = Company(
        name="Owned Company",
        website="https://owned.com",
        user_id=user.id,
    )
    async_session.add(company_owned)
    await async_session.commit()
    await async_session.refresh(company_owned)

    # Create global company
    company_global = Company(
        name="Global Company",
        website="https://global.com",
        user_id=None,
    )
    async_session.add(company_global)
    await async_session.commit()
    await async_session.refresh(company_global)

    # Anonymous user cannot access owned company
    result_owned = await check_company_access(company_owned.id, None, async_session)
    assert result_owned is None

    # Anonymous user can access global company
    result_global = await check_company_access(company_global.id, None, async_session)
    assert result_global is not None
    assert result_global.id == company_global.id


@pytest.mark.asyncio
async def test_check_company_access_invalid_uuid(
    async_session: AsyncSession,
) -> None:
    """Test that invalid UUID returns None."""
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    result = await check_company_access("invalid-uuid", user, async_session)
    assert result is None


@pytest.mark.asyncio
async def test_check_news_access_user_owns_company(
    async_session: AsyncSession,
) -> None:
    """Test that user can access news from their own company."""
    from datetime import datetime, timezone

    # Create user
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create company owned by user
    company = Company(
        name="Test Company",
        website="https://test.com",
        user_id=user.id,
    )
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)

    # Create news for company
    news = NewsItem(
        title="Test News",
        summary="Summary",
        content="Content",
        source_url="https://test.com/news",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=company.id,
        published_at=datetime.now(timezone.utc),
    )
    async_session.add(news)
    await async_session.commit()
    await async_session.refresh(news)

    # Check access
    result = await check_news_access(news.id, user, async_session)

    assert result is not None
    assert result.id == news.id
    assert result.title == news.title


@pytest.mark.asyncio
async def test_check_news_access_user_does_not_own_company(
    async_session: AsyncSession,
) -> None:
    """Test that user cannot access news from another user's company."""
    from datetime import datetime, timezone

    # Create two users
    user1 = User(email="user1@example.com", hashed_password="hashed")
    user2 = User(email="user2@example.com", hashed_password="hashed")
    async_session.add(user1)
    async_session.add(user2)
    await async_session.commit()
    await async_session.refresh(user1)
    await async_session.refresh(user2)

    # Create company owned by user1
    company = Company(
        name="User1 Company",
        website="https://user1.com",
        user_id=user1.id,
    )
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)

    # Create news for user1's company
    news = NewsItem(
        title="User1 News",
        summary="Summary",
        content="Content",
        source_url="https://user1.com/news",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=company.id,
        published_at=datetime.now(timezone.utc),
    )
    async_session.add(news)
    await async_session.commit()
    await async_session.refresh(news)

    # User2 tries to access user1's news
    result = await check_news_access(news.id, user2, async_session)

    assert result is None


@pytest.mark.asyncio
async def test_check_news_access_news_not_found(
    async_session: AsyncSession,
) -> None:
    """Test that non-existent news returns None."""
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    fake_news_id = uuid4()
    result = await check_news_access(fake_news_id, user, async_session)

    assert result is None


@pytest.mark.asyncio
async def test_check_news_access_invalid_uuid(
    async_session: AsyncSession,
) -> None:
    """Test that invalid UUID returns None."""
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    result = await check_news_access("invalid-uuid", user, async_session)
    assert result is None


@pytest.mark.asyncio
async def test_get_user_company_ids(
    async_session: AsyncSession,
) -> None:
    """Test that get_user_company_ids returns only user's companies."""
    # Create two users
    user1 = User(email="user1@example.com", hashed_password="hashed")
    user2 = User(email="user2@example.com", hashed_password="hashed")
    async_session.add(user1)
    async_session.add(user2)
    await async_session.commit()
    await async_session.refresh(user1)
    await async_session.refresh(user2)

    # Create companies for user1
    company1 = Company(
        name="User1 Company 1",
        website="https://user1-1.com",
        user_id=user1.id,
    )
    company2 = Company(
        name="User1 Company 2",
        website="https://user1-2.com",
        user_id=user1.id,
    )
    async_session.add(company1)
    async_session.add(company2)
    await async_session.commit()
    await async_session.refresh(company1)
    await async_session.refresh(company2)

    # Create company for user2
    company3 = Company(
        name="User2 Company",
        website="https://user2.com",
        user_id=user2.id,
    )
    async_session.add(company3)
    await async_session.commit()
    await async_session.refresh(company3)

    # Get user1's companies
    user1_companies = await get_user_company_ids(user1, async_session)

    assert len(user1_companies) == 2
    assert company1.id in user1_companies
    assert company2.id in user1_companies
    assert company3.id not in user1_companies

    # Get user2's companies
    user2_companies = await get_user_company_ids(user2, async_session)

    assert len(user2_companies) == 1
    assert company3.id in user2_companies
    assert company1.id not in user2_companies
    assert company2.id not in user2_companies


@pytest.mark.asyncio
async def test_get_user_company_ids_no_companies(
    async_session: AsyncSession,
) -> None:
    """Test that get_user_company_ids returns empty list for user with no companies."""
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    companies = await get_user_company_ids(user, async_session)

    assert companies == []


@pytest.mark.asyncio
async def test_get_user_company_ids_excludes_global_companies(
    async_session: AsyncSession,
) -> None:
    """Test that get_user_company_ids excludes global companies (user_id is None)."""
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create user-owned company
    company_owned = Company(
        name="Owned Company",
        website="https://owned.com",
        user_id=user.id,
    )
    async_session.add(company_owned)
    await async_session.commit()
    await async_session.refresh(company_owned)

    # Create global company
    company_global = Company(
        name="Global Company",
        website="https://global.com",
        user_id=None,
    )
    async_session.add(company_global)
    await async_session.commit()
    await async_session.refresh(company_global)

    # Get user's companies
    companies = await get_user_company_ids(user, async_session)

    assert len(companies) == 1
    assert company_owned.id in companies
    assert company_global.id not in companies





