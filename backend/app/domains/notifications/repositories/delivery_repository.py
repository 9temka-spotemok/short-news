"""Repository helpers for notification deliveries."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    NotificationChannel,
    NotificationDelivery,
    NotificationDeliveryStatus,
)


class DeliveryRepository:
    """Data access for notification deliveries."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, delivery: NotificationDelivery) -> NotificationDelivery:
        self._session.add(delivery)
        await self._session.flush()
        return delivery

    async def get(self, delivery_id) -> Optional[NotificationDelivery]:
        result = await self._session.execute(
            select(NotificationDelivery).where(NotificationDelivery.id == delivery_id)
        )
        return result.scalar_one_or_none()

    async def get_pending(self, *, now: datetime, limit: int) -> List[NotificationDelivery]:
        result = await self._session.execute(
            select(NotificationDelivery)
            .join(NotificationChannel)
            .where(
                and_(
                    NotificationChannel.disabled == False,
                    NotificationChannel.is_verified == True,
                    or_(
                        NotificationDelivery.status == NotificationDeliveryStatus.PENDING,
                        and_(
                            NotificationDelivery.status == NotificationDeliveryStatus.RETRYING,
                            NotificationDelivery.next_retry_at <= now,
                        ),
                    ),
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())


