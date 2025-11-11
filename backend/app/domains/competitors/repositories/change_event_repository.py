"""
Repository helpers for competitor change events.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ChangeNotificationStatus,
    ChangeProcessingStatus,
    CompetitorChangeEvent,
    SourceType,
)


@dataclass
class ChangeEventRepository:
    session: AsyncSession

    async def list_change_events(
        self,
        company_id: UUID,
        *,
        limit: int = 20,
        status: Optional[ChangeProcessingStatus] = None,
    ) -> List[CompetitorChangeEvent]:
        query = (
            select(CompetitorChangeEvent)
            .where(CompetitorChangeEvent.company_id == company_id)
            .order_by(desc(CompetitorChangeEvent.detected_at))
            .limit(limit)
        )
        if status:
            query = query.where(CompetitorChangeEvent.processing_status == status)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_change_event(
        self,
        *,
        company_id: UUID,
        source_type: SourceType,
        change_summary: str,
        changed_fields: List[Dict],
        raw_diff: Dict,
        detected_at: datetime,
        current_snapshot_id: Optional[UUID],
        previous_snapshot_id: Optional[UUID],
        processing_status: ChangeProcessingStatus,
        notification_status: ChangeNotificationStatus,
    ) -> CompetitorChangeEvent:
        event = CompetitorChangeEvent(
            company_id=company_id,
            source_type=source_type,
            change_summary=change_summary,
            changed_fields=changed_fields,
            raw_diff=raw_diff,
            detected_at=detected_at,
            current_snapshot_id=current_snapshot_id,
            previous_snapshot_id=previous_snapshot_id,
            processing_status=processing_status,
            notification_status=notification_status,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def fetch_by_id(
        self,
        event_id: UUID,
        *,
        with_snapshots: bool = False,
    ) -> Optional[CompetitorChangeEvent]:
        query = select(CompetitorChangeEvent).where(
            CompetitorChangeEvent.id == event_id
        )
        if with_snapshots:
            query = query.options(
                selectinload(CompetitorChangeEvent.current_snapshot),
                selectinload(CompetitorChangeEvent.previous_snapshot),
            )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def save(self, event: CompetitorChangeEvent) -> CompetitorChangeEvent:
        self.session.add(event)
        await self.session.flush()
        return event

