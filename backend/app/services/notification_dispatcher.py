"""
Notification dispatcher for multi-channel delivery with deduplication and retries.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from loguru import logger
from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert
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


class NotificationDispatcher:
    """Coordinates notification events and channel deliveries."""

    PRIORITY_ORDER: Dict[NotificationPriority, int] = {
        NotificationPriority.LOW: 1,
        NotificationPriority.MEDIUM: 2,
        NotificationPriority.HIGH: 3,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_channel(
        self,
        *,
        user_id,
        channel_type: NotificationChannelType,
        destination: str,
        metadata: Optional[dict] = None,
        verified: bool = False,
    ) -> NotificationChannel:
        """Create or update notification channel."""
        stmt = insert(NotificationChannel).values(
            user_id=user_id,
            channel_type=channel_type,
            destination=destination,
            metadata=metadata or {},
            is_verified=verified,
            verified_at=datetime.utcnow() if verified else None,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_notification_channel_destination",
            set_={
                "metadata": stmt.excluded.metadata,
                "is_verified": stmt.excluded.is_verified,
                "verified_at": stmt.excluded.verified_at,
                "disabled": False,
                "updated_at": datetime.utcnow(),
            },
        )
        await self.db.execute(stmt)
        await self.db.commit()

        channel = await self._get_channel(user_id=user_id, channel_type=channel_type, destination=destination)
        assert channel, "Failed to upsert notification channel"
        return channel

    async def _get_channel(
        self, *, user_id, channel_type: NotificationChannelType, destination: str
    ) -> Optional[NotificationChannel]:
        result = await self.db.execute(
            select(NotificationChannel).where(
                and_(
                    NotificationChannel.user_id == user_id,
                    NotificationChannel.channel_type == channel_type,
                    NotificationChannel.destination == destination,
                )
            )
        )
        return result.scalar_one_or_none()

    async def disable_channel(self, channel_id) -> None:
        """Soft-disable channel to prevent further deliveries."""
        result = await self.db.execute(
            select(NotificationChannel).where(NotificationChannel.id == channel_id)
        )
        channel = result.scalar_one_or_none()
        if channel:
            channel.disabled = True
            await self.db.commit()

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
        """
        Queue notification event with optional deduplication.

        Returns None when deduplication suppresses a duplicate event.
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl_seconds)

        if deduplication_key:
            duplicate = await self._find_active_duplicate(user_id, notification_type, deduplication_key)
            if duplicate:
                logger.debug(
                    "Suppressing duplicate event for user=%s type=%s key=%s",
                    user_id,
                    notification_type,
                    deduplication_key,
                )
                return None

        event = NotificationEvent(
            user_id=user_id,
            notification_type=notification_type,
            priority=priority,
            payload=payload,
            deduplication_key=deduplication_key,
            status=NotificationEventStatus.QUEUED,
            expires_at=expires_at,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        await self._fan_out_deliveries(event)
        return event

    async def _find_active_duplicate(
        self,
        user_id,
        notification_type: NotificationType,
        deduplication_key: str,
    ) -> Optional[NotificationEvent]:
        result = await self.db.execute(
            select(NotificationEvent).where(
                and_(
                    NotificationEvent.user_id == user_id,
                    NotificationEvent.notification_type == notification_type,
                    NotificationEvent.deduplication_key == deduplication_key,
                    NotificationEvent.status.in_(
                        [NotificationEventStatus.QUEUED, NotificationEventStatus.DISPATCHED]
                    ),
                    or_(NotificationEvent.expires_at.is_(None), NotificationEvent.expires_at > datetime.utcnow()),
                )
            )
        )
        return result.scalar_one_or_none()

    async def _fan_out_deliveries(self, event: NotificationEvent) -> None:
        """Create deliveries for all matching subscriptions."""
        subscriptions = await self._matching_subscriptions(
            user_id=event.user_id,
            notification_type=event.notification_type,
            min_priority=event.priority,
            payload=event.payload,
        )

        if not subscriptions:
            logger.debug(
                "No subscriptions found for event %s (user=%s type=%s)",
                event.id,
                event.user_id,
                event.notification_type,
            )
            event.status = NotificationEventStatus.SUPPRESSED
            await self.db.commit()
            return

        deliveries: List[NotificationDelivery] = []
        for subscription in subscriptions:
            if subscription.channel.disabled or not subscription.channel.is_verified:
                continue
            delivery = NotificationDelivery(
                event_id=event.id,
                channel_id=subscription.channel_id,
                status=NotificationDeliveryStatus.PENDING,
                attempt=0,
            )
            deliveries.append(delivery)
            self.db.add(delivery)

        if deliveries:
            event.status = NotificationEventStatus.DISPATCHED
            event.dispatched_at = datetime.utcnow()
            await self.db.commit()
            for delivery in deliveries:
                await self.db.refresh(delivery)
        else:
            event.status = NotificationEventStatus.SUPPRESSED
            await self.db.commit()

    async def _matching_subscriptions(
        self,
        *,
        user_id,
        notification_type: NotificationType,
        min_priority: NotificationPriority,
        payload: dict,
    ) -> List[NotificationSubscription]:
        result = await self.db.execute(
            select(NotificationSubscription)
            .join(NotificationChannel)
            .where(
                and_(
                    NotificationSubscription.user_id == user_id,
                    NotificationSubscription.notification_type == notification_type,
                    NotificationSubscription.enabled == True,
                )
            )
        )
        subscriptions = list(result.scalars().all())

        allowed: List[NotificationSubscription] = []
        for subscription in subscriptions:
            if (
                self.PRIORITY_ORDER.get(subscription.min_priority, 0)
                > self.PRIORITY_ORDER.get(min_priority, 0)
            ):
                continue
            if not self._filters_match(subscription.filters or {}, payload):
                continue
            allowed.append(subscription)
        return allowed

    def _filters_match(self, filters: Dict[str, Dict[str, str]], payload: dict) -> bool:
        """
        Evaluate user-defined filters against payload.

        Current implementation supports:
            - categories: list of allowed categories in payload["category"]
            - companies: list of allowed company ids in payload["company_id"]
        """
        if not filters:
            return True

        category_filters = filters.get("categories")
        if category_filters and payload.get("category") not in category_filters:
            return False

        company_filters = filters.get("companies")
        if company_filters and payload.get("company_id") not in company_filters:
            return False

        return True

    async def mark_delivery_sent(
        self,
        delivery_id,
        *,
        response_metadata: Optional[dict] = None,
    ) -> Optional[NotificationDelivery]:
        result = await self.db.execute(
            select(NotificationDelivery).where(NotificationDelivery.id == delivery_id)
        )
        delivery = result.scalar_one_or_none()
        if not delivery:
            return None

        delivery.status = NotificationDeliveryStatus.SENT
        delivery.response_metadata = response_metadata or {}
        delivery.last_attempt_at = datetime.utcnow()

        event = delivery.event
        if all(d.status == NotificationDeliveryStatus.SENT for d in event.deliveries):
            event.status = NotificationEventStatus.DELIVERED
            event.delivered_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(delivery)
        return delivery

    async def mark_delivery_failed(
        self,
        delivery_id,
        *,
        error_message: str,
        retry_in_seconds: Optional[int] = None,
        max_attempts: int = 3,
    ) -> Optional[NotificationDelivery]:
        result = await self.db.execute(
            select(NotificationDelivery).where(NotificationDelivery.id == delivery_id)
        )
        delivery = result.scalar_one_or_none()
        if not delivery:
            return None

        now = datetime.utcnow()
        delivery.attempt += 1
        delivery.last_attempt_at = now
        delivery.error_message = error_message

        if retry_in_seconds and delivery.attempt < max_attempts:
            delivery.status = NotificationDeliveryStatus.RETRYING
            delivery.next_retry_at = now + timedelta(seconds=retry_in_seconds)
        else:
            delivery.status = NotificationDeliveryStatus.FAILED
            delivery.next_retry_at = None
            event = delivery.event
            if all(d.status in {NotificationDeliveryStatus.SENT, NotificationDeliveryStatus.FAILED} for d in event.deliveries):
                if any(d.status == NotificationDeliveryStatus.SENT for d in event.deliveries):
                    event.status = NotificationEventStatus.DELIVERED
                    event.delivered_at = now
                else:
                    event.status = NotificationEventStatus.FAILED
                    event.error_message = error_message

        await self.db.commit()
        await self.db.refresh(delivery)
        return delivery

    async def get_pending_deliveries(self, limit: int = 50) -> List[NotificationDelivery]:
        """Fetch deliveries that are pending or ready to retry."""
        now = datetime.utcnow()
        result = await self.db.execute(
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


