"""
Domain-level ingestion helpers for competitor pricing snapshots.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import hashlib
from loguru import logger
from app.models import (
    ChangeProcessingStatus,
    SourceType,
)
from app.utils.snapshots import persist_snapshot
from ..repositories import (
    ChangeEventRepository,
    PricingSnapshotRepository,
)
from app.parsers.pricing import PricingPageParser
from .change_service import CompetitorChangeDomainService
from .notification_service import CompetitorNotificationService
from .diff_engine import (
    compute_hash,
    compute_diff,
    has_changes,
    build_summary,
    flatten_changes,
)
from app.models import Company


class CompetitorIngestionDomainService:
    """Coordinates ingestion of competitor pricing pages."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        change_service: Optional[CompetitorChangeDomainService] = None,
        notification_service: Optional[CompetitorNotificationService] = None,
        snapshot_repo: Optional[PricingSnapshotRepository] = None,
        change_event_repo: Optional[ChangeEventRepository] = None,
        parser: Optional[PricingPageParser] = None,
    ) -> None:
        self._session = session
        self._change_service = change_service or CompetitorChangeDomainService(session)
        self._notification_service = notification_service
        self._snapshot_repo = snapshot_repo or PricingSnapshotRepository(session)
        self._change_repo = change_event_repo or ChangeEventRepository(session)
        self._parser = parser or PricingPageParser()

    async def ingest_pricing_page(
        self,
        *,
        company_id: UUID,
        source_url: str,
        html: str,
        source_type: SourceType,
    ):
        """Persist pricing snapshot, compute diff and create change event."""
        now = datetime.now(timezone.utc)

        parse_result = self._parser.parse(html, url=source_url)
        normalized_plans: List[Dict[str, Any]] = [
            plan.to_dict() for plan in parse_result.plans
        ]
        data_hash = compute_hash(normalized_plans)
        previous_snapshot = await self._snapshot_repo.fetch_latest(company_id, source_url)

        previous_data = (
            previous_snapshot.normalized_data if previous_snapshot else []
        )
        diff = compute_diff(previous_data, normalized_plans)
        has_real_changes = has_changes(diff)
        change_summary = build_summary(diff)
        changed_fields = flatten_changes(diff)

        result = await self._session.execute(
            select(Company.name).where(Company.id == company_id)
        )
        company_label = result.scalar_one_or_none() or str(company_id)
        snapshot_path = persist_snapshot(
            scope="pricing",
            company_identifier=company_label,
            source_id=_snapshot_identifier(source_type, source_url),
            url=source_url,
            html=html,
        )

        snapshot = await self._snapshot_repo.create_snapshot(
            company_id=company_id,
            source_url=source_url,
            source_type=source_type,
            parser_version=self._parser.VERSION,
            extracted_at=now,
            normalized_data=normalized_plans,
            data_hash=data_hash,
            raw_snapshot_url=snapshot_path,
            extraction_metadata={
                **parse_result.extraction_metadata,
                "company_label": company_label,
                "source_url": source_url,
            },
            warnings=parse_result.warnings,
            processing_status=ChangeProcessingStatus.SUCCESS
            if has_real_changes
            else ChangeProcessingStatus.SKIPPED,
            processing_notes=None,
        )

        event = await self._change_service.create_change_event(
            company_id=company_id,
            source_type=source_type,
            diff=diff,
            detected_at=now,
            current_snapshot_id=snapshot.id,
            previous_snapshot_id=previous_snapshot.id if previous_snapshot else None,
        )

        await self._session.commit()
        await self._session.refresh(event)

        if self._notification_service:
            try:
                await self._notification_service.dispatch_change_event(event)
            except Exception:  # pragma: no cover - defensive logging
                logger.exception(
                    "Failed to dispatch competitor change notifications | event=%s",
                    event.id,
                )
            finally:
                await self._session.refresh(event)

        return event


def _snapshot_identifier(source_type: SourceType, source_url: str) -> str:
    digest = hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:10]
    return f"{source_type.value}_{digest}"

