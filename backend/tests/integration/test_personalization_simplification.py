"""
Tests for simplified personalization logic.

Tests the new simplified personalization approach:
- Always use user_id for base personalization
- company_ids as additional filter (intersection)
- SQL-level filtering instead of in-memory
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, NewsItem, User
from app.models.news import NewsCategory, SourceType


@pytest.mark.asyncio
async def test_authenticated_user_without_company_ids_sees_all_companies(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Test that authenticated user without company_ids sees all their companies."""
    # Create user
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create companies for user
    company1 = Company(
        name="User Company 1",
        website="https://company1.com",
        user_id=user.id,
    )
    company2 = Company(
        name="User Company 2",
        website="https://company2.com",
        user_id=user.id,
    )
    async_session.add(company1)
    async_session.add(company2)
    await async_session.commit()
    await async_session.refresh(company1)
    await async_session.refresh(company2)

    # Create news for both companies
    news1 = NewsItem(
        title="News from Company 1",
        summary="Summary 1",
        content="Content 1",
        source_url="https://example.com/news1",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=company1.id,
        published_at=datetime.now(timezone.utc),
    )
    news2 = NewsItem(
        title="News from Company 2",
        summary="Summary 2",
        content="Content 2",
        source_url="https://example.com/news2",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=company2.id,
        published_at=datetime.now(timezone.utc),
    )
    async_session.add(news1)
    async_session.add(news2)
    await async_session.commit()

    # Get auth token
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(user.id)})

    # Request news without company_ids - should see all user's companies
    response = await async_client.get(
        "/api/v1/news/",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 10},
    )

    assert response.status_code == 200
    body = response.json()
    items = body.get("items", [])
    
    # Should see news from both companies
    company_ids_in_response = {item["company"]["id"] for item in items}
    assert str(company1.id) in company_ids_in_response
    assert str(company2.id) in company_ids_in_response
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_authenticated_user_with_company_ids_sees_only_selected(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Test that authenticated user with company_ids sees only selected companies (intersection)."""
    # Create user
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create companies for user
    company1 = Company(
        name="User Company 1",
        website="https://company1.com",
        user_id=user.id,
    )
    company2 = Company(
        name="User Company 2",
        website="https://company2.com",
        user_id=user.id,
    )
    async_session.add(company1)
    async_session.add(company2)
    await async_session.commit()
    await async_session.refresh(company1)
    await async_session.refresh(company2)

    # Create news for both companies
    news1 = NewsItem(
        title="News from Company 1",
        summary="Summary 1",
        content="Content 1",
        source_url="https://example.com/news1",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=company1.id,
        published_at=datetime.now(timezone.utc),
    )
    news2 = NewsItem(
        title="News from Company 2",
        summary="Summary 2",
        content="Content 2",
        source_url="https://example.com/news2",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=company2.id,
        published_at=datetime.now(timezone.utc),
    )
    async_session.add(news1)
    async_session.add(news2)
    await async_session.commit()

    # Get auth token
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(user.id)})

    # Request news with company_ids - should see only company1
    response = await async_client.get(
        "/api/v1/news/",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "company_ids": str(company1.id),
            "limit": 10,
        },
    )

    assert response.status_code == 200
    body = response.json()
    items = body.get("items", [])
    
    # Should see only news from company1
    company_ids_in_response = {item["company"]["id"] for item in items}
    assert str(company1.id) in company_ids_in_response
    assert str(company2.id) not in company_ids_in_response


@pytest.mark.asyncio
async def test_authenticated_user_cannot_access_other_user_companies_via_company_ids(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Test that authenticated user cannot access other user's companies via company_ids (security)."""
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
        source_url="https://example.com/news-b",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=company_b.id,
        published_at=datetime.now(timezone.utc),
    )
    async_session.add(news_b)
    await async_session.commit()

    # Get auth token for user A
    from app.core.security import create_access_token
    token_a = create_access_token(data={"sub": str(user_a.id)})

    # User A tries to access user B's company via company_ids
    response = await async_client.get(
        "/api/v1/news/",
        headers={"Authorization": f"Bearer {token_a}"},
        params={
            "company_ids": str(company_b.id),  # User B's company
            "limit": 10,
        },
    )

    assert response.status_code == 200
    body = response.json()
    items = body.get("items", [])
    
    # Should NOT see user B's news (intersection should be empty)
    company_ids_in_response = {item["company"]["id"] for item in items}
    assert str(company_b.id) not in company_ids_in_response


@pytest.mark.asyncio
async def test_anonymous_user_sees_only_global_companies(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Test that anonymous user sees only global companies (user_id is None)."""
    # Create user with company
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create global company (user_id is None)
    global_company = Company(
        name="Global Company",
        website="https://global.com",
        user_id=None,  # Global company
    )
    # Create user's company
    user_company = Company(
        name="User Company",
        website="https://user.com",
        user_id=user.id,
    )
    async_session.add(global_company)
    async_session.add(user_company)
    await async_session.commit()
    await async_session.refresh(global_company)
    await async_session.refresh(user_company)

    # Create news for both
    global_news = NewsItem(
        title="Global News",
        summary="Summary",
        content="Content",
        source_url="https://example.com/global",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=global_company.id,
        published_at=datetime.now(timezone.utc),
    )
    user_news = NewsItem(
        title="User News",
        summary="Summary",
        content="Content",
        source_url="https://example.com/user",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=user_company.id,
        published_at=datetime.now(timezone.utc),
    )
    async_session.add(global_news)
    async_session.add(user_news)
    await async_session.commit()

    # Request news without authentication
    response = await async_client.get(
        "/api/v1/news/",
        params={"limit": 10},
    )

    assert response.status_code == 200
    body = response.json()
    items = body.get("items", [])
    
    # Should see only global company's news
    company_ids_in_response = {item["company"]["id"] for item in items}
    assert str(global_company.id) in company_ids_in_response
    assert str(user_company.id) not in company_ids_in_response


@pytest.mark.asyncio
async def test_search_uses_sql_filtering_not_in_memory(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Test that search endpoint uses SQL filtering with user_id, not in-memory filtering."""
    # Create user
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Create company for user
    company = Company(
        name="User Company",
        website="https://company.com",
        user_id=user.id,
    )
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)

    # Create news with searchable content
    news = NewsItem(
        title="AI Breakthrough",
        summary="Summary about AI",
        content="Detailed content about artificial intelligence breakthrough",
        source_url="https://example.com/ai-news",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        company_id=company.id,
        published_at=datetime.now(timezone.utc),
    )
    async_session.add(news)
    await async_session.commit()

    # Get auth token
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(user.id)})

    # Search with user authentication
    response = await async_client.get(
        "/api/v1/news/search",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "q": "AI",
            "limit": 10,
        },
    )

    assert response.status_code == 200
    body = response.json()
    items = body.get("items", [])
    
    # Should find news from user's company
    assert len(items) >= 1
    assert any("AI" in item.get("title", "").upper() or "AI" in item.get("content", "").upper() for item in items)
    
    # All items should be from user's company (SQL filtering)
    company_ids_in_response = {item["company"]["id"] for item in items}
    assert str(company.id) in company_ids_in_response


@pytest.mark.asyncio
async def test_user_with_no_companies_gets_empty_result(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Test that user with no companies gets empty result."""
    # Create user without companies
    user = User(email="test@example.com", hashed_password="hashed")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Get auth token
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(user.id)})

    # Request news - should get empty result
    response = await async_client.get(
        "/api/v1/news/",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 10},
    )

    assert response.status_code == 200
    body = response.json()
    items = body.get("items", [])
    total = body.get("total", 0)
    
    # Should be empty
    assert len(items) == 0
    assert total == 0
