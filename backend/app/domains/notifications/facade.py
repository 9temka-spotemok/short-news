"""Notifications domain facade coordinating legacy notification services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.services import (
    DispatcherService,
    NotificationService,
    DigestService,
)
from app.services.notification_delivery_executor import NotificationDeliveryExecutor


@dataclass
class NotificationsFacade:
    """Entry point for notification operations used by API and Celery."""

    session: AsyncSession

    # ------------------------------------------------------------------
    # Legacy service accessors
    # ------------------------------------------------------------------
    @property
    def notification_service(self) -> NotificationService:
        return NotificationService(self.session)

    @property
    def dispatcher(self) -> DispatcherService:
        return DispatcherService(self.session)

    @property
    def digest_service(self) -> DigestService:
        return DigestService(self.session)

    @property
    def delivery_executor(self) -> NotificationDeliveryExecutor:
        return NotificationDeliveryExecutor(self.session)

    # ------------------------------------------------------------------
    # Convenience helpers for API consumers
    # ------------------------------------------------------------------
    async def mark_notification_as_read(self, notification_id: str, user_id: str) -> bool:
        return await self.notification_service.mark_as_read(notification_id, user_id)

    async def mark_all_notifications_as_read(self, user_id: str) -> int:
        return await self.notification_service.mark_all_as_read(user_id)

    async def queue_notification_event(
        self,
        *,
        user_id: str,
        notification_type,
        priority,
        payload: dict,
        deduplication_key: Optional[str] = None,
        ttl_seconds: int = 3600,
    ):
        return await self.dispatcher.queue_event(
            user_id=user_id,
            notification_type=notification_type,
            priority=priority,
            payload=payload,
            deduplication_key=deduplication_key,
            ttl_seconds=ttl_seconds,
        )

    async def disable_channel(self, channel_id) -> None:
        await self.dispatcher.disable_channel(channel_id)

