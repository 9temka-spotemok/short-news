"""Repository helpers for notification channels."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationChannel, NotificationChannelType


class ChannelRepository:
    """Data access layer for notification channels."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert_channel(
        self,
        *,
        user_id,
        channel_type: NotificationChannelType,
        destination: str,
        metadata: Optional[dict],
        verified: bool,
    ) -> NotificationChannel:
        """Create or update a channel, returning the persisted entity."""
        now = datetime.now(timezone.utc)
        stmt = insert(NotificationChannel).values(
            user_id=user_id,
            channel_type=channel_type,
            destination=destination,
            metadata=metadata or {},
            is_verified=verified,
            verified_at=now if verified else None,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_notification_channel_destination",
            set_={
                "metadata": stmt.excluded.metadata,
                "is_verified": stmt.excluded.is_verified,
                "verified_at": stmt.excluded.verified_at,
                "disabled": False,
                "updated_at": now,
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()
        channel = await self.get_channel(
            user_id=user_id,
            channel_type=channel_type,
            destination=destination,
        )
        if channel is None:
            raise RuntimeError("Failed to upsert notification channel")
        return channel

    async def get_channel(
        self,
        *,
        user_id,
        channel_type: NotificationChannelType,
        destination: str,
    ) -> Optional[NotificationChannel]:
        result = await self._session.execute(
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
        result = await self._session.execute(
            select(NotificationChannel).where(NotificationChannel.id == channel_id)
        )
        channel = result.scalar_one_or_none()
        if channel:
            channel.disabled = True
            await self._session.commit()


