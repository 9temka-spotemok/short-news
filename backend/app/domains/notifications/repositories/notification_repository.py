"""Repository helpers for Notification records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification


class NotificationRecordRepository:
    """CRUD operations for user notifications."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, notification: Notification) -> Notification:
        self._session.add(notification)
        await self._session.commit()
        await self._session.refresh(notification)
        return notification

    async def get_for_user(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> Optional[Notification]:
        result = await self._session.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def mark_as_read(self, notification: Notification) -> None:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await self._session.commit()

    async def mark_all_as_read(self, user_id: UUID) -> int:
        result = await self._session.execute(
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                )
            )
            .values(
                is_read=True,
                read_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            .returning(Notification.id)
        )
        await self._session.commit()
        return len(result.scalars().all())

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        skip: int,
        limit: int,
        unread_only: bool = False,
    ) -> List[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)
        stmt = stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_user(self, user_id: UUID, *, unread_only: bool = False) -> int:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)
        result = await self._session.execute(stmt)
        return len(result.scalars().all())


