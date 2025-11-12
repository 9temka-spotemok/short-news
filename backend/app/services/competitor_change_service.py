"""
Service for competitor pricing snapshots and change detection.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ChangeProcessingStatus,
    Company,
    CompetitorChangeEvent,
    SourceType,
)
from app.domains.competitors.services.change_service import (
    CompetitorChangeDomainService,
)
from app.domains.competitors.services.ingestion_service import (
    CompetitorIngestionDomainService,
)
from app.domains.competitors.services.notification_service import (
    CompetitorNotificationService,
)


class CompetitorChangeService:
    """Legacy wrapper around domain competitor change services."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._domain_change = CompetitorChangeDomainService(db)
        self._domain_ingestion = CompetitorIngestionDomainService(
            db,
            change_service=self._domain_change,
            notification_service=CompetitorNotificationService(db),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def list_change_events(
        self,
        company_id: uuid.UUID,
        limit: int = 20,
        status: Optional[ChangeProcessingStatus] = None,
    ) -> List[CompetitorChangeEvent]:
        return await self._domain_change.list_change_events(
            company_id,
            limit=limit,
            status=status,
        )

    async def list_change_events_payload(
        self,
        company_id: uuid.UUID,
        limit: int = 20,
        status: Optional[ChangeProcessingStatus] = None,
    ) -> List[Dict[str, Any]]:
        return await self._domain_change.list_change_events_payload(
            company_id,
            limit=limit,
            status=status,
        )

    async def paginate_change_events_payload(
        self,
        company_id: uuid.UUID,
        *,
        limit: int = 20,
        status: Optional[ChangeProcessingStatus] = None,
        cursor_detected_at: Optional[datetime] = None,
        cursor_event_id: Optional[uuid.UUID] = None,
        source_types: Optional[Sequence[SourceType]] = None,
    ) -> Tuple[List[Dict[str, Any]], bool, int]:
        return await self._domain_change.paginate_change_events_payload(
            company_id,
            limit=limit,
            status=status,
            cursor_detected_at=cursor_detected_at,
            cursor_event_id=cursor_event_id,
            source_types=source_types,
        )

    async def fetch_change_event_payload(
        self,
        event_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        return await self._domain_change.fetch_change_event_payload(event_id)

    async def process_pricing_page(
        self,
        company_id: uuid.UUID,
        source_url: str,
        source_type: SourceType,
        html: str,
    ) -> CompetitorChangeEvent:
        return await self._domain_ingestion.ingest_pricing_page(
            company_id=company_id,
            source_url=source_url,
            html=html,
            source_type=source_type,
        )

    async def recompute_diff(
        self,
        event_id: uuid.UUID,
    ) -> Optional[CompetitorChangeEvent]:
        return await self._domain_change.recompute_change_event(event_id)

