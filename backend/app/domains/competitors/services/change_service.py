"""
Domain-level wrapper for competitor change detection.

This class delegates to the legacy `CompetitorChangeService` while the bounded
context is being restructured. It allows the facade to depend on a domain
service rather than the legacy implementation directly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence, Dict, Any, List, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ChangeNotificationStatus,
    ChangeProcessingStatus,
    CompetitorChangeEvent,
    SourceType,
)
from ..repositories import ChangeEventRepository, PricingSnapshotRepository
from .diff_engine import (
    build_summary,
    compute_diff,
    flatten_changes,
    has_changes,
)


class CompetitorChangeDomainService:
    """Domain-native implementation of pricing diff logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._change_repo = ChangeEventRepository(session)
        self._snapshot_repo = PricingSnapshotRepository(session)

    async def list_change_events(
        self,
        company_id: UUID,
        *,
        limit: int = 20,
        status: Optional[ChangeProcessingStatus] = None,
    ):
        return await self._change_repo.list_change_events(
            company_id,
            limit=limit,
            status=status,
        )

    async def list_change_events_payload(
        self,
        company_id: UUID,
        *,
        limit: int = 20,
        status: Optional[ChangeProcessingStatus] = None,
    ) -> List[Dict[str, Any]]:
        return await self._change_repo.list_change_events_serialised(
            company_id,
            limit=limit,
            status=status,
        )

    async def paginate_change_events_payload(
        self,
        company_id: UUID,
        *,
        limit: int = 20,
        status: Optional[ChangeProcessingStatus] = None,
        cursor_detected_at: Optional[datetime] = None,
        cursor_event_id: Optional[UUID] = None,
        source_types: Optional[Sequence[SourceType]] = None,
    ) -> Tuple[List[Dict[str, Any]], bool, int]:
        events, has_more = await self._change_repo.paginate_change_events_serialised(
            company_id,
            limit=limit,
            status=status,
            cursor_detected_at=cursor_detected_at,
            cursor_event_id=cursor_event_id,
            source_types=source_types,
        )
        total = await self._change_repo.count_change_events(
            company_id,
            status=status,
            source_types=source_types,
        )
        return events, has_more, total

    async def fetch_change_event_payload(
        self,
        event_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        return await self._change_repo.fetch_serialised_by_id(event_id)

    async def recompute_change_event(self, event_id: UUID):
        event = await self._change_repo.fetch_by_id(
            event_id,
            with_snapshots=True,
        )
        if not event or not event.current_snapshot:
            return None

        previous_data = (
            event.previous_snapshot.normalized_data
            if event.previous_snapshot
            else []
        )
        current_data = event.current_snapshot.normalized_data or []
        diff = compute_diff(previous_data, current_data)
        has_real_changes = has_changes(diff)

        event.change_summary = build_summary(diff)
        event.changed_fields = flatten_changes(diff)
        event.raw_diff = diff
        event.processing_status = (
            ChangeProcessingStatus.SUCCESS
            if has_real_changes
            else ChangeProcessingStatus.SKIPPED
        )
        event.notification_status = (
            ChangeNotificationStatus.PENDING
            if has_real_changes
            else ChangeNotificationStatus.SKIPPED
        )

        await self._change_repo.save(event)
        await self._session.commit()
        await self._session.refresh(event)
        return event

    async def create_change_event(
        self,
        *,
        company_id: UUID,
        source_type,
        diff: Dict[str, Any],
        detected_at: datetime,
        current_snapshot_id: Optional[UUID],
        previous_snapshot_id: Optional[UUID],
    ) -> CompetitorChangeEvent:
        summary = build_summary(diff)
        flattened = flatten_changes(diff)
        has_real_changes = has_changes(diff)

        event = await self._change_repo.create_change_event(
            company_id=company_id,
            source_type=source_type,
            change_summary=summary
            if has_real_changes
            else "No significant changes detected",
            changed_fields=flattened if has_real_changes else [],
            raw_diff=diff if has_real_changes else {},
            detected_at=detected_at,
            current_snapshot_id=current_snapshot_id,
            previous_snapshot_id=previous_snapshot_id,
            processing_status=ChangeProcessingStatus.SUCCESS
            if has_real_changes
            else ChangeProcessingStatus.SKIPPED,
            notification_status=ChangeNotificationStatus.PENDING
            if has_real_changes
            else ChangeNotificationStatus.SKIPPED,
        )
        return event

