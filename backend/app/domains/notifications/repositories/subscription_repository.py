"""Repository helpers for notification subscriptions."""

from __future__ import annotations

from typing import List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    NotificationChannel,
    NotificationSubscription,
    NotificationType,
)


class SubscriptionRepository:
    """Data access for notification subscriptions."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_enabled_for_user(
        self,
        *,
        user_id,
        notification_type: NotificationType,
    ) -> List[NotificationSubscription]:
        result = await self._session.execute(
            select(NotificationSubscription)
            .options(selectinload(NotificationSubscription.channel))
            .join(NotificationChannel)
            .where(
                and_(
                    NotificationSubscription.user_id == user_id,
                    NotificationSubscription.notification_type == notification_type,
                    NotificationSubscription.enabled == True,
                )
            )
        )
        return list(result.scalars().all())


