"""
Notification dispatcher for multi-channel delivery with deduplication and retries.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    NotificationChannel,
    NotificationChannelType,
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationEventStatus,
    NotificationPriority,
    NotificationSubscription,
    NotificationType,
)
from app.domains.notifications.services import DispatcherService


class NotificationDispatcher:
    """Legacy adapter that delegates to the domain dispatcher service."""

    PRIORITY_ORDER: Dict[NotificationPriority, int] = DispatcherService.PRIORITY_ORDER

    def __init__(self, db: AsyncSession):
        self._service = DispatcherService(db)

    async def upsert_channel(
        self,
        *,
        user_id,
        channel_type: NotificationChannelType,
        destination: str,
        metadata: Optional[dict] = None,
        verified: bool = False,
    ) -> NotificationChannel:
        return await self._service.upsert_channel(
            user_id=user_id,
            channel_type=channel_type,
            destination=destination,
            metadata=metadata,
            verified=verified,
        )

    async def disable_channel(self, channel_id) -> None:
        await self._service.disable_channel(channel_id)

    async def queue_event(
        self,
        *,
        user_id,
        notification_type: NotificationType,
        priority: NotificationPriority,
        payload: dict,
        deduplication_key: Optional[str] = None,
        ttl_seconds: int = 3600,
    ) -> Optional[NotificationEvent]:
        return await self._service.queue_event(
            user_id=user_id,
            notification_type=notification_type,
            priority=priority,
            payload=payload,
            deduplication_key=deduplication_key,
            ttl_seconds=ttl_seconds,
        )

    async def mark_delivery_sent(
        self,
        delivery_id,
        *,
        response_metadata: Optional[dict] = None,
    ) -> Optional[NotificationDelivery]:
        return await self._service.mark_delivery_sent(
            delivery_id,
            response_metadata=response_metadata,
        )

    async def mark_delivery_failed(
        self,
        delivery_id,
        *,
        error_message: str,
        retry_in_seconds: Optional[int] = None,
        max_attempts: int = 3,
    ) -> Optional[NotificationDelivery]:
        return await self._service.mark_delivery_failed(
            delivery_id,
            error_message=error_message,
            retry_in_seconds=retry_in_seconds,
            max_attempts=max_attempts,
        )

    async def get_pending_deliveries(self, limit: int = 50) -> List[NotificationDelivery]:
        return await self._service.get_pending_deliveries(limit=limit)


