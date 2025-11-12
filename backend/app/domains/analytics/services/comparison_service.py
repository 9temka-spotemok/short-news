"""Domain-level comparison service bridging legacy analytics comparison logic."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics_comparison_service import AnalyticsComparisonService as LegacyComparisonService
from app.models import SourceType
from app.schemas.competitor_events import CompetitorChangeEventSchema

from .snapshot_service import SnapshotService


class ComparisonService(LegacyComparisonService):
    """
    Thin domain wrapper over the legacy comparison service.

    Until the remaining logic is fully migrated, we reuse the proven
    implementation and simply swap the snapshot service dependency with the
    new domain-level `SnapshotService`.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        # Override legacy dependency with the domain snapshot service.
        self.analytics_service = SnapshotService(session)

    async def get_change_log_page(
        self,
        company_id: UUID,
        *,
        limit: int,
        cursor_detected_at: Optional[datetime] = None,
        cursor_event_id: Optional[UUID] = None,
        source_types: Optional[Sequence[SourceType]] = None,
    ) -> Tuple[List[CompetitorChangeEventSchema], bool, int]:
        rows, has_more, total = await self.change_service.paginate_change_events_payload(
            company_id,
            limit=limit,
            cursor_detected_at=cursor_detected_at,
            cursor_event_id=cursor_event_id,
            source_types=source_types,
        )
        events = [
            CompetitorChangeEventSchema.model_validate(row) for row in rows
        ]
        return events, has_more, total

