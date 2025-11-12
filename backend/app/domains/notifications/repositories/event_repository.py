"""Repository helpers for notification events."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationEventStatus,
    NotificationType,
)


class EventRepository:
    """Data access for notification events and deliveries metadata."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_event(self, event: NotificationEvent) -> NotificationEvent:
        self._session.add(event)
        await self._session.commit()
        await self._session.refresh(event)
        return event

    async def find_active_duplicate(
        self,
        *,
        user_id,
        notification_type: NotificationType,
        deduplication_key: str,
        now: datetime,
    ) -> Optional[NotificationEvent]:
        result = await self._session.execute(
            select(NotificationEvent).where(
                and_(
                    NotificationEvent.user_id == user_id,
                    NotificationEvent.notification_type == notification_type,
                    NotificationEvent.deduplication_key == deduplication_key,
                    NotificationEvent.status.in_(
                        [NotificationEventStatus.QUEUED, NotificationEventStatus.DISPATCHED]
                    ),
                    or_(
                        NotificationEvent.expires_at.is_(None),
                        NotificationEvent.expires_at > now,
                    ),
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_event_status(
        self,
        event: NotificationEvent,
        *,
        status: NotificationEventStatus,
        timestamp: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> NotificationEvent:
        event.status = status
        if status == NotificationEventStatus.DISPATCHED:
            event.dispatched_at = timestamp
        elif status == NotificationEventStatus.DELIVERED:
            event.delivered_at = timestamp
        elif status == NotificationEventStatus.FAILED:
            event.error_message = error_message
        await self._session.commit()
        await self._session.refresh(event)
        return event

    async def update_delivery(self, delivery: NotificationDelivery) -> NotificationDelivery:
        await self._session.commit()
        await self._session.refresh(delivery)
        return delivery

    @staticmethod
    def all_deliveries_succeeded(event: NotificationEvent) -> bool:
        return all(d.status == NotificationDeliveryStatus.SENT for d in event.deliveries)

    @staticmethod
    def any_delivery_succeeded(event: NotificationEvent) -> bool:
        return any(d.status == NotificationDeliveryStatus.SENT for d in event.deliveries)


