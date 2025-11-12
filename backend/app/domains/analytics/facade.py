"""Analytics domain facade coordinating snapshot and comparison services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalyticsPeriod, CompanyAnalyticsSnapshot, SourceType
from app.schemas.analytics import (
    AnalyticsExportRequest,
    AnalyticsExportResponse,
    ComparisonRequest,
    ComparisonResponse,
)
from app.schemas.competitor_events import CompetitorChangeEventSchema
from app.models import User

from .services import ComparisonService, SnapshotService


@dataclass
class AnalyticsFacade:
    """Facade aggregating analytics domain operations for API and Celery layers."""

    session: AsyncSession

    # ------------------------------------------------------------------
    # Snapshot operations
    # ------------------------------------------------------------------
    @property
    def snapshots(self) -> SnapshotService:
        return SnapshotService(self.session)

    async def get_snapshots(
        self,
        company_id: UUID,
        period: AnalyticsPeriod,
        limit: int,
    ) -> List[CompanyAnalyticsSnapshot]:
        return await self.snapshots.get_snapshots(company_id, period, limit)

    async def get_latest_snapshot(
        self,
        company_id: UUID,
        period: AnalyticsPeriod,
    ) -> Optional[CompanyAnalyticsSnapshot]:
        return await self.snapshots.get_latest_snapshot(company_id, period)

    async def refresh_company_snapshots(
        self,
        company_id: UUID,
        period: AnalyticsPeriod,
        lookback: int,
    ) -> List[CompanyAnalyticsSnapshot]:
        return await self.snapshots.refresh_company_snapshots(company_id, period, lookback)

    async def sync_knowledge_graph(
        self,
        company_id: UUID,
        period_start: datetime,
        period: AnalyticsPeriod,
    ) -> int:
        return await self.snapshots.sync_knowledge_graph(company_id, period_start, period)

    # ------------------------------------------------------------------
    # Comparison / export operations
    # ------------------------------------------------------------------
    @property
    def comparisons(self) -> ComparisonService:
        return ComparisonService(self.session)

    async def build_comparison(
        self,
        payload: ComparisonRequest,
        user: User,
    ) -> ComparisonResponse:
        return await self.comparisons.build_comparison(payload, user=user)

    async def build_export_payload(
        self,
        payload: AnalyticsExportRequest,
        user: User,
    ) -> AnalyticsExportResponse:
        return await self.comparisons.build_export_payload(payload, user=user)

    async def get_change_log(
        self,
        company_id: UUID,
        *,
        limit: int,
        cursor_detected_at: Optional[datetime] = None,
        cursor_event_id: Optional[UUID] = None,
        source_types: Optional[Sequence[SourceType]] = None,
    ) -> Tuple[List[CompetitorChangeEventSchema], bool, int]:
        return await self.comparisons.get_change_log_page(
            company_id=company_id,
            limit=limit,
            cursor_detected_at=cursor_detected_at,
            cursor_event_id=cursor_event_id,
            source_types=source_types,
        )

