"""Domain-level notification dispatcher handling events and deliveries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.repositories import (
    ChannelRepository,
    SubscriptionRepository,
    EventRepository,
    DeliveryRepository,
)
from app.models import (
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationEventStatus,
    NotificationPriority,
    NotificationSubscription,
    NotificationType,
    NotificationChannelType,
    NotificationChannel,
)


class DispatcherService:
    """Coordinates notification events and channel deliveries."""

    PRIORITY_ORDER: Dict[NotificationPriority, int] = {
        NotificationPriority.LOW: 1,
        NotificationPriority.MEDIUM: 2,
        NotificationPriority.HIGH: 3,
    }

    def __init__(self, session: AsyncSession):
        self._session = session
        self._channels = ChannelRepository(session)
        self._subscriptions = SubscriptionRepository(session)
        self._events = EventRepository(session)
        self._deliveries = DeliveryRepository(session)

    # ------------------------------------------------------------------
    # Channel management
    # ------------------------------------------------------------------
    async def upsert_channel(
        self,
        *,
        user_id,
        channel_type: NotificationChannelType,
        destination: str,
        metadata: Optional[dict] = None,
        verified: bool = False,
    ) -> NotificationChannel:
        return await self._channels.upsert_channel(
            user_id=user_id,
            channel_type=channel_type,
            destination=destination,
            metadata=metadata,
            verified=verified,
        )

    async def disable_channel(self, channel_id) -> None:
        """Soft-disable channel to prevent further deliveries."""
        await self._channels.disable_channel(channel_id)

    # ------------------------------------------------------------------
    # Event lifecycle
    # ------------------------------------------------------------------
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
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)

        if deduplication_key:
            duplicate = await self._events.find_active_duplicate(
                user_id=user_id,
                notification_type=notification_type,
                deduplication_key=deduplication_key,
                now=now,
            )
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
        event = await self._events.create_event(event)

        await self._fan_out_deliveries(event, now)
        return event

    # ------------------------------------------------------------------
    # Delivery management
    # ------------------------------------------------------------------
    async def _fan_out_deliveries(self, event: NotificationEvent, now: datetime) -> None:
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
            await self._events.update_event_status(
                event,
                status=NotificationEventStatus.SUPPRESSED,
            )
            return

        deliveries: List[NotificationDelivery] = []
        for subscription in subscriptions:
            channel = getattr(subscription, "channel", None)
            if channel is None:
                logger.warning(
                    "Subscription %s for user %s has no channel bound; suppressing event %s",
                    subscription.id,
                    subscription.user_id,
                    event.id,
                )
                await self._events.update_event_status(
                    event,
                    status=NotificationEventStatus.SUPPRESSED,
                )
                return

            if channel.disabled or not channel.is_verified:
                continue

            delivery = NotificationDelivery(
                event_id=event.id,
                channel_id=subscription.channel_id,
                status=NotificationDeliveryStatus.PENDING,
                attempt=0,
            )
            deliveries.append(await self._deliveries.add(delivery))

        if deliveries:
            await self._session.commit()
            for delivery in deliveries:
                await self._session.refresh(delivery)

            await self._events.update_event_status(
                event,
                status=NotificationEventStatus.DISPATCHED,
                timestamp=now,
            )
        else:
            await self._events.update_event_status(
                event,
                status=NotificationEventStatus.SUPPRESSED,
            )

    async def _matching_subscriptions(
        self,
        *,
        user_id,
        notification_type: NotificationType,
        min_priority: NotificationPriority,
        payload: dict,
    ) -> List[NotificationSubscription]:
        subscriptions = await self._subscriptions.list_enabled_for_user(
            user_id=user_id,
            notification_type=notification_type,
        )

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

    @staticmethod
    def _filters_match(filters: Dict[str, Dict[str, str]], payload: dict) -> bool:
        """
        Evaluate user-defined filters against payload.

        Supports:
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
        delivery = await self._deliveries.get(delivery_id)
        if not delivery:
            return None

        now = datetime.now(timezone.utc)
        delivery.status = NotificationDeliveryStatus.SENT
        delivery.response_metadata = response_metadata or {}
        delivery.last_attempt_at = now

        await self._session.commit()
        await self._session.refresh(delivery)

        event = delivery.event
        if self._events.all_deliveries_succeeded(event):
            await self._events.update_event_status(
                event,
                status=NotificationEventStatus.DELIVERED,
                timestamp=now,
            )

        return delivery

    async def mark_delivery_failed(
        self,
        delivery_id,
        *,
        error_message: str,
        retry_in_seconds: Optional[int] = None,
        max_attempts: int = 3,
    ) -> Optional[NotificationDelivery]:
        delivery = await self._deliveries.get(delivery_id)
        if not delivery:
            return None

        now = datetime.now(timezone.utc)
        delivery.attempt += 1
        delivery.last_attempt_at = now
        delivery.error_message = error_message

        event = delivery.event

        if retry_in_seconds and delivery.attempt < max_attempts:
            delivery.status = NotificationDeliveryStatus.RETRYING
            delivery.next_retry_at = now + timedelta(seconds=retry_in_seconds)
            await self._session.commit()
            await self._session.refresh(delivery)
            return delivery

        delivery.status = NotificationDeliveryStatus.FAILED
        delivery.next_retry_at = None

        await self._session.commit()
        await self._session.refresh(delivery)

        if all(
            d.status in {NotificationDeliveryStatus.SENT, NotificationDeliveryStatus.FAILED}
            for d in event.deliveries
        ):
            if self._events.any_delivery_succeeded(event):
                await self._events.update_event_status(
                    event,
                    status=NotificationEventStatus.DELIVERED,
                    timestamp=now,
                )
            else:
                await self._events.update_event_status(
                    event,
                    status=NotificationEventStatus.FAILED,
                    timestamp=now,
                    error_message=error_message,
                )

        return delivery

    async def get_pending_deliveries(self, limit: int = 50) -> List[NotificationDelivery]:
        """Fetch deliveries that are pending or ready to retry."""
        now = datetime.now(timezone.utc)
        return await self._deliveries.get_pending(now=now, limit=limit)