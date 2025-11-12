"""
Repository helpers for competitor change events.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload, selectinload

from app.models import (
    ChangeNotificationStatus,
    ChangeProcessingStatus,
    CompetitorChangeEvent,
    CompetitorPricingSnapshot,
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

        query = query.options(
            joinedload(CompetitorChangeEvent.current_snapshot),
            joinedload(CompetitorChangeEvent.previous_snapshot),
        )

        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def list_change_events_serialised(
        self,
        company_id: UUID,
        *,
        limit: int = 20,
        status: Optional[ChangeProcessingStatus] = None,
    ) -> List[Dict[str, Any]]:
        rows = await self._fetch_change_events_rows(
            company_id,
            limit=limit,
            status=status,
        )
        return self._serialise_rows(rows)

    async def paginate_change_events_serialised(
        self,
        company_id: UUID,
        *,
        limit: int = 20,
        status: Optional[ChangeProcessingStatus] = None,
        cursor_detected_at: Optional[datetime] = None,
        cursor_event_id: Optional[UUID] = None,
        source_types: Optional[Sequence[SourceType]] = None,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        rows = await self._fetch_change_events_rows(
            company_id,
            limit=limit + 1,
            status=status,
            cursor_detected_at=cursor_detected_at,
            cursor_event_id=cursor_event_id,
            source_types=source_types,
        )
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]
        return self._serialise_rows(rows), has_more

    async def count_change_events(
        self,
        company_id: UUID,
        *,
        status: Optional[ChangeProcessingStatus] = None,
        source_types: Optional[Sequence[SourceType]] = None,
    ) -> int:
        stmt = select(func.count()).select_from(CompetitorChangeEvent).where(
            CompetitorChangeEvent.company_id == company_id
        )
        if status:
            stmt = stmt.where(CompetitorChangeEvent.processing_status == status)
        if source_types:
            stmt = stmt.where(CompetitorChangeEvent.source_type.in_(source_types))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def _fetch_change_events_rows(
        self,
        company_id: UUID,
        *,
        limit: int,
        status: Optional[ChangeProcessingStatus] = None,
        cursor_detected_at: Optional[datetime] = None,
        cursor_event_id: Optional[UUID] = None,
        source_types: Optional[Sequence[SourceType]] = None,
    ) -> List[Dict[str, Any]]:
        def _query(sync_session):
            current_snapshot = aliased(
                CompetitorPricingSnapshot, name="current_snapshot"
            )
            previous_snapshot = aliased(
                CompetitorPricingSnapshot, name="previous_snapshot"
            )

            stmt = (
                select(
                    CompetitorChangeEvent.id.label("id"),
                    CompetitorChangeEvent.company_id.label("company_id"),
                    CompetitorChangeEvent.source_type.label("source_type"),
                    CompetitorChangeEvent.change_summary.label("change_summary"),
                    CompetitorChangeEvent.changed_fields.label("changed_fields"),
                    CompetitorChangeEvent.raw_diff.label("raw_diff"),
                    CompetitorChangeEvent.detected_at.label("detected_at"),
                    CompetitorChangeEvent.processing_status.label("processing_status"),
                    CompetitorChangeEvent.notification_status.label(
                        "notification_status"
                    ),
                    current_snapshot.id.label("current_id"),
                    current_snapshot.parser_version.label("current_parser_version"),
                    current_snapshot.raw_snapshot_url.label("current_raw_snapshot_url"),
                    current_snapshot.extraction_metadata.label(
                        "current_extraction_metadata"
                    ),
                    current_snapshot.warnings.label("current_warnings"),
                    current_snapshot.processing_status.label(
                        "current_processing_status"
                    ),
                    previous_snapshot.id.label("previous_id"),
                    previous_snapshot.parser_version.label("previous_parser_version"),
                    previous_snapshot.raw_snapshot_url.label(
                        "previous_raw_snapshot_url"
                    ),
                    previous_snapshot.extraction_metadata.label(
                        "previous_extraction_metadata"
                    ),
                    previous_snapshot.warnings.label("previous_warnings"),
                    previous_snapshot.processing_status.label(
                        "previous_processing_status"
                    ),
                )
                .select_from(CompetitorChangeEvent)
                .outerjoin(
                    current_snapshot,
                    current_snapshot.id == CompetitorChangeEvent.current_snapshot_id,
                )
                .outerjoin(
                    previous_snapshot,
                    previous_snapshot.id == CompetitorChangeEvent.previous_snapshot_id,
                )
                .where(CompetitorChangeEvent.company_id == company_id)
            )
            if status:
                stmt = stmt.where(CompetitorChangeEvent.processing_status == status)
            if source_types:
                stmt = stmt.where(CompetitorChangeEvent.source_type.in_(source_types))
            if cursor_detected_at is not None:
                cursor_dt = cursor_detected_at.replace(tzinfo=None)
                stmt = stmt.where(
                    or_(
                        CompetitorChangeEvent.detected_at < cursor_dt,
                        and_(
                            CompetitorChangeEvent.detected_at == cursor_dt,
                            CompetitorChangeEvent.id < cursor_event_id,
                        ),
                    )
                )

            stmt = stmt.order_by(
                desc(CompetitorChangeEvent.detected_at),
                desc(CompetitorChangeEvent.id),
            ).limit(limit)

            result = sync_session.execute(stmt)
            return result.mappings().all()

        return await self.session.run_sync(_query)

    def _serialise_rows(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payload: List[Dict[str, Any]] = []
        for row in rows:
            payload.append(
                {
                    "id": row["id"],
                    "company_id": row["company_id"],
                    "source_type": row["source_type"],
                    "change_summary": row["change_summary"],
                    "changed_fields": row["changed_fields"] or [],
                    "raw_diff": row["raw_diff"] or {},
                    "detected_at": row["detected_at"],
                    "processing_status": row["processing_status"],
                    "notification_status": row["notification_status"],
                    "current_snapshot": self._snapshot_payload(
                        row["current_id"],
                        row["current_parser_version"],
                        row["current_raw_snapshot_url"],
                        row["current_extraction_metadata"],
                        row["current_warnings"],
                        row["current_processing_status"],
                    ),
                    "previous_snapshot": self._snapshot_payload(
                        row["previous_id"],
                        row["previous_parser_version"],
                        row["previous_raw_snapshot_url"],
                        row["previous_extraction_metadata"],
                        row["previous_warnings"],
                        row["previous_processing_status"],
                    ),
                }
            )
        return payload

    async def fetch_serialised_by_id(
        self,
        event_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        def _fetch_company_id(sync_session):
            stmt = select(CompetitorChangeEvent.company_id).where(
                CompetitorChangeEvent.id == event_id
            )
            result = sync_session.execute(stmt)
            return result.scalar_one_or_none()

        company_id = await self.session.run_sync(_fetch_company_id)
        if not company_id:
            return None
        events = await self.list_change_events_serialised(
            company_id,
            limit=1,
            status=None,
        )
        return events[0] if events and events[0]["id"] == event_id else None

    @staticmethod
    def _snapshot_payload(
        snapshot_id,
        parser_version,
        raw_snapshot_url,
        extraction_metadata,
        warnings,
        processing_status,
    ) -> Optional[Dict[str, Any]]:
        if not snapshot_id:
            return None
        return {
            "id": snapshot_id,
            "parser_version": parser_version,
            "raw_snapshot_url": raw_snapshot_url,
            "extraction_metadata": extraction_metadata or {},
            "warnings": warnings or [],
            "processing_status": processing_status,
        }

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

