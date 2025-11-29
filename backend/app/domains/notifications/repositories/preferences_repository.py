"""Repository helpers for user notification preferences."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserPreferences


class UserPreferencesRepository:
    """Data access for UserPreferences."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, user_id: UUID) -> Optional[UserPreferences]:
        result = await self._session.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_subscribed_to_company(self, company_id: UUID) -> List[UserPreferences]:
        result = await self._session.execute(
            select(UserPreferences).where(UserPreferences.subscribed_companies.contains([company_id]))
        )
        return list(result.scalars().all())

    async def list_interested_in_category(self, category: str) -> List[UserPreferences]:
        # PostgreSQL requires explicit type casting when comparing enum arrays
        # Use raw SQL with explicit cast to newscategory enum type
        # The @> operator checks if the array contains the specified value
        result = await self._session.execute(
            text("""
                SELECT id FROM user_preferences 
                WHERE interested_categories @> ARRAY[CAST(:category AS newscategory)]
            """),
            {"category": category}
        )
        # Get IDs and fetch full objects using ORM
        ids = [row[0] for row in result.all()]
        if not ids:
            return []
        
        # Fetch full UserPreferences objects using ORM
        result = await self._session.execute(
            select(UserPreferences).where(UserPreferences.id.in_(ids))
        )
        return list(result.scalars().all())

    async def create_default(self, user_id: UUID) -> UserPreferences:
        from uuid import uuid4
        from app.models.preferences import DigestFrequency, NotificationFrequency

        preferences = UserPreferences(
            id=uuid4(),
            user_id=user_id,
            subscribed_companies=[],
            interested_categories=[],
            keywords=[],
            notification_frequency=NotificationFrequency.DAILY,
            digest_enabled=True,
            digest_frequency=DigestFrequency.DAILY,
            digest_custom_schedule={},
            digest_format="short",
            digest_include_summaries=True,
            telegram_chat_id=None,
            telegram_enabled=False,
            timezone="UTC",
            week_start_day=0,
        )
        self._session.add(preferences)
        await self._session.commit()
        await self._session.refresh(preferences)
        return preferences

