"""Repository helpers for notification settings."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationSettings


class NotificationSettingsRepository:
    """Data access for NotificationSettings."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, user_id: UUID) -> Optional[NotificationSettings]:
        result = await self._session.execute(
            select(NotificationSettings).where(NotificationSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_enabled(self) -> List[NotificationSettings]:
        result = await self._session.execute(
            select(NotificationSettings).where(NotificationSettings.enabled == True)
        )
        return list(result.scalars().all())

    async def save(self, settings: NotificationSettings) -> NotificationSettings:
        self._session.add(settings)
        await self._session.commit()
        await self._session.refresh(settings)
        return settings


