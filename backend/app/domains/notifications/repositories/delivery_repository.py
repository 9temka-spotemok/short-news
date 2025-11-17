"""Repository helpers for notification deliveries."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import ProgrammingError
from loguru import logger
import asyncpg

from app.models import (
    NotificationChannel,
    NotificationDelivery,
    NotificationDeliveryStatus,
)
from app.core.db_utils import table_exists


class DeliveryRepository:
    """Data access for notification deliveries."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._table_exists_cache: Optional[bool] = None

    async def _check_table_exists(self) -> bool:
        """Check if notification_deliveries table exists."""
        if self._table_exists_cache is None:
            self._table_exists_cache = await table_exists(self._session, "notification_deliveries")
        return self._table_exists_cache

    async def add(self, delivery: NotificationDelivery) -> NotificationDelivery:
        if not await self._check_table_exists():
            logger.warning("Table notification_deliveries does not exist, skipping add operation")
            raise RuntimeError("Table notification_deliveries does not exist. Please run migrations.")
        self._session.add(delivery)
        await self._session.flush()
        return delivery

    async def get(self, delivery_id) -> Optional[NotificationDelivery]:
        if not await self._check_table_exists():
            logger.warning("Table notification_deliveries does not exist, returning None")
            return None
        result = await self._session.execute(
            select(NotificationDelivery).where(NotificationDelivery.id == delivery_id)
        )
        return result.scalar_one_or_none()

    async def get_pending(self, *, now: datetime, limit: int) -> List[NotificationDelivery]:
        if not await self._check_table_exists():
            logger.warning("Table notification_deliveries does not exist, returning empty list")
            return []
        
        try:
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
        except ProgrammingError as e:
            # Check if this is an UndefinedTableError (table doesn't exist)
            error_msg = str(e).lower()
            is_table_missing = (
                "does not exist" in error_msg
                or "undefinedtable" in error_msg
                or "relation" in error_msg and "does not exist" in error_msg
                or (hasattr(e, "orig") and e.orig is not None 
                    and isinstance(e.orig, asyncpg.exceptions.UndefinedTableError))
            )
            
            if is_table_missing:
                logger.warning(
                    "Table notification_deliveries does not exist. "
                    "Please run migrations or create the table manually. "
                    "See create_notification_deliveries.sql or run: python -m alembic upgrade head"
                )
                # Invalidate cache
                self._table_exists_cache = False
                return []
            # Re-raise if it's a different ProgrammingError
            raise
        except Exception as e:
            # Catch any other database-related errors that might indicate missing table
            error_msg = str(e).lower()
            if "does not exist" in error_msg or "undefinedtable" in error_msg or "relation" in error_msg:
                logger.warning(
                    f"Table notification_deliveries appears to be missing: {e}. "
                    "Please run migrations or create the table manually."
                )
                self._table_exists_cache = False
                return []
            raise


