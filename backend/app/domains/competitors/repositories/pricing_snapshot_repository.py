"""
Repository helpers for competitor pricing snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CompetitorPricingSnapshot, SourceType


@dataclass
class PricingSnapshotRepository:
    session: AsyncSession

    async def fetch_latest(
        self,
        company_id: UUID,
        source_url: str,
    ) -> Optional[CompetitorPricingSnapshot]:
        query = (
            select(CompetitorPricingSnapshot)
            .where(
                CompetitorPricingSnapshot.company_id == company_id,
                CompetitorPricingSnapshot.source_url == source_url,
            )
            .order_by(desc(CompetitorPricingSnapshot.extracted_at))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_snapshot(
        self,
        *,
        company_id: UUID,
        source_url: str,
        source_type: SourceType,
        parser_version: str,
        extracted_at: datetime,
        normalized_data: Optional[List[Dict]],
        data_hash: Optional[str],
        raw_snapshot_url: Optional[str],
        extraction_metadata: Dict,
        warnings: List[str],
        processing_status,
        processing_notes: Optional[str] = None,
    ) -> CompetitorPricingSnapshot:
        snapshot = CompetitorPricingSnapshot(
            company_id=company_id,
            source_url=source_url,
            source_type=source_type,
            parser_version=parser_version,
            extracted_at=extracted_at,
            normalized_data=normalized_data,
            data_hash=data_hash,
            raw_snapshot_url=raw_snapshot_url,
            extraction_metadata=extraction_metadata,
            warnings=warnings,
            processing_status=processing_status,
            processing_notes=processing_notes,
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def fetch_by_id(
        self,
        snapshot_id: UUID,
    ) -> Optional[CompetitorPricingSnapshot]:
        query = select(CompetitorPricingSnapshot).where(
            CompetitorPricingSnapshot.id == snapshot_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()



