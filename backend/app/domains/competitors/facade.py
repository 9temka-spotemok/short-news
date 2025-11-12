"""
Competitor domain facade.

Provides a stable entry point for API layers and background tasks to interact
with competitor analysis functionality while we gradually migrate legacy
services into a proper bounded context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.competitor_service import CompetitorAnalysisService
from app.models import ChangeProcessingStatus, SourceType
from .services import (
    CompetitorChangeDomainService,
    CompetitorIngestionDomainService,
    CompetitorNotificationService,
)


@dataclass
class CompetitorFacade:
    """Facade coordinating competitor analysis and change tracking services."""

    session: AsyncSession

    @property
    def analysis_service(self) -> CompetitorAnalysisService:
        return CompetitorAnalysisService(self.session)

    @property
    def change_service(self) -> CompetitorChangeDomainService:
        return CompetitorChangeDomainService(self.session)

    @property
    def notification_service(self) -> CompetitorNotificationService:
        return CompetitorNotificationService(self.session)

    @property
    def ingestion_service(self) -> CompetitorIngestionDomainService:
        return CompetitorIngestionDomainService(
            self.session,
            change_service=self.change_service,
            notification_service=self.notification_service,
        )

    async def ingest_pricing_page(
        self,
        company_id: str,
        *,
        source_url: str,
        html: str,
        source_type: SourceType,
    ):
        return await self.ingestion_service.ingest_pricing_page(
            company_id=UUID(company_id),
            source_url=source_url,
            html=html,
            source_type=source_type,
        )

    async def compare_companies(
        self,
        company_ids: List[str],
        *,
        date_from: datetime,
        date_to: datetime,
        user_id: Optional[str] = None,
        comparison_name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await self.analysis_service.compare_companies(
            company_ids=company_ids,
            date_from=date_from,
            date_to=date_to,
            user_id=user_id,
            comparison_name=comparison_name,
            filters=filters,
        )

    async def get_user_comparisons(
        self,
        user_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        return await self.analysis_service.get_user_comparisons(user_id, limit)

    async def get_comparison(
        self,
        comparison_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        return await self.analysis_service.get_comparison(comparison_id, user_id)

    async def delete_comparison(
        self,
        comparison_id: str,
        user_id: str,
    ) -> bool:
        return await self.analysis_service.delete_comparison(comparison_id, user_id)

    async def build_company_activity(
        self,
        company_id: UUID,
        *,
        date_from: datetime,
        date_to: datetime,
        top_news_limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        news_volume = await self.analysis_service.get_news_volume(
            company_id,
            date_from,
            date_to,
            filters=filters,
        )
        category_distribution = await self.analysis_service.get_category_distribution(
            company_id,
            date_from,
            date_to,
            filters=filters,
        )
        activity_score = await self.analysis_service.get_activity_score(
            company_id,
            date_from,
            date_to,
            filters=filters,
        )
        daily_activity = await self.analysis_service.get_daily_activity(
            company_id,
            date_from,
            date_to,
            filters=filters,
        )
        top_news = await self.analysis_service.get_top_news(
            company_id,
            date_from,
            date_to,
            limit=top_news_limit,
            filters=filters,
        )

        return {
            "news_volume": news_volume,
            "category_distribution": category_distribution,
            "activity_score": activity_score,
            "daily_activity": daily_activity,
            "top_news": top_news,
        }

    async def suggest_competitors(
        self,
        company_id: UUID,
        *,
        limit: int,
        date_from: datetime,
        date_to: datetime,
    ) -> List[Dict[str, Any]]:
        return await self.analysis_service.suggest_competitors(
            company_id=company_id,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
        )

    async def analyze_news_themes(
        self,
        company_ids: List[UUID],
        *,
        date_from: datetime,
        date_to: datetime,
    ) -> Dict[str, Any]:
        return await self.analysis_service.analyze_news_themes(
            company_ids=company_ids,
            date_from=date_from,
            date_to=date_to,
        )

    async def list_change_events(
        self,
        company_id: UUID,
        *,
        limit: int,
        status: Optional[ChangeProcessingStatus] = None,
    ):
        return await self.change_service.list_change_events(
            company_id,
            limit=limit,
            status=status,
        )

    async def list_change_events_payload(
        self,
        company_id: UUID,
        *,
        limit: int,
        status: Optional[ChangeProcessingStatus] = None,
    ) -> List[Dict[str, Any]]:
        return await self.change_service.list_change_events_payload(
            company_id,
            limit=limit,
            status=status,
        )

    async def fetch_change_event_payload(
        self,
        event_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        return await self.change_service.fetch_change_event_payload(event_id)

    async def recompute_change_event(self, event_id: UUID):
        return await self.change_service.recompute_change_event(event_id)

    async def notify_change_event(self, event_id: UUID | str) -> int:
        """Trigger notifications for a previously detected change event."""
        return await self.notification_service.dispatch_change_event(event_id)

