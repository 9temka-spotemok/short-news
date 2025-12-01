"""
Manual test script for access_control functions.
This script can be run without pytest dependencies.
"""

import asyncio
import sys
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, '.')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.models import Base, User, Company, NewsItem
from app.models.news import NewsCategory, SourceType
from app.core.access_control import (
    check_company_access,
    check_news_access,
    get_user_company_ids,
)

# Use SQLite for testing
SQLITE_URL = "sqlite+aiosqlite:///:memory:"


async def test_access_control():
    """Test access control functions."""
    print("=" * 60)
    print("Testing access_control functions")
    print("=" * 60)
    
    # Create engine and session
    engine = create_async_engine(SQLITE_URL, echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session_maker() as session:
        # Create test users
        user1 = User(email="user1@test.com", hashed_password="hashed1")
        user2 = User(email="user2@test.com", hashed_password="hashed2")
        session.add(user1)
        session.add(user2)
        await session.commit()
        await session.refresh(user1)
        await session.refresh(user2)
        
        print(f"\n✓ Created users: {user1.email}, {user2.email}")
        
        # Create companies
        company1 = Company(
            name="User1 Company",
            website="https://user1.com",
            user_id=user1.id,
        )
        company2 = Company(
            name="User2 Company",
            website="https://user2.com",
            user_id=user2.id,
        )
        company_global = Company(
            name="Global Company",
            website="https://global.com",
            user_id=None,  # Global company
        )
        session.add(company1)
        session.add(company2)
        session.add(company_global)
        await session.commit()
        await session.refresh(company1)
        await session.refresh(company2)
        await session.refresh(company_global)
        
        print(f"✓ Created companies: {company1.name}, {company2.name}, {company_global.name}")
        
        # Test 1: check_company_access - user can access own company
        print("\n--- Test 1: User can access own company ---")
        result = await check_company_access(company1.id, user1, session)
        assert result is not None, "User1 should access own company"
        assert result.id == company1.id, "Should return correct company"
        print("✓ PASS: User1 can access own company")
        
        # Test 2: check_company_access - user cannot access other user's company
        print("\n--- Test 2: User cannot access other user's company ---")
        result = await check_company_access(company2.id, user1, session)
        assert result is None, "User1 should NOT access user2's company"
        print("✓ PASS: User1 cannot access user2's company")
        
        # Test 3: check_company_access - user can access global company
        print("\n--- Test 3: User can access global company ---")
        result = await check_company_access(company_global.id, user1, session)
        assert result is not None, "User1 should access global company"
        assert result.id == company_global.id, "Should return global company"
        print("✓ PASS: User1 can access global company")
        
        # Test 4: get_user_company_ids
        print("\n--- Test 4: get_user_company_ids returns only user's companies ---")
        company_ids = await get_user_company_ids(user1, session)
        assert company1.id in company_ids, "Should include user1's company"
        assert company2.id not in company_ids, "Should NOT include user2's company"
        assert company_global.id not in company_ids, "Should NOT include global company"
        print(f"✓ PASS: User1 has {len(company_ids)} companies")
        
        # Test 5: check_news_access - user can access news from own company
        print("\n--- Test 5: User can access news from own company ---")
        from datetime import datetime, timezone
        news1 = NewsItem(
            title="User1 News",
            summary="Summary",
            content="Content",
            source_url="https://user1.com/news",
            source_type=SourceType.BLOG,
            category=NewsCategory.PRODUCT_UPDATE,
            company_id=company1.id,
            published_at=datetime.now(timezone.utc),
        )
        session.add(news1)
        await session.commit()
        await session.refresh(news1)
        
        result = await check_news_access(news1.id, user1, session)
        assert result is not None, "User1 should access own news"
        assert result.id == news1.id, "Should return correct news"
        print("✓ PASS: User1 can access news from own company")
        
        # Test 6: check_news_access - user cannot access news from other user's company
        print("\n--- Test 6: User cannot access news from other user's company ---")
        news2 = NewsItem(
            title="User2 News",
            summary="Summary",
            content="Content",
            source_url="https://user2.com/news",
            source_type=SourceType.BLOG,
            category=NewsCategory.PRODUCT_UPDATE,
            company_id=company2.id,
            published_at=datetime.now(timezone.utc),
        )
        session.add(news2)
        await session.commit()
        await session.refresh(news2)
        
        result = await check_news_access(news2.id, user1, session)
        assert result is None, "User1 should NOT access user2's news"
        print("✓ PASS: User1 cannot access news from user2's company")
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_access_control())





