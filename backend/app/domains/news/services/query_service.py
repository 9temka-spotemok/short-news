"""
Query service for the news domain.

Provides high-level read operations backed by ``NewsRepository``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import (
    NewsItem,
    NewsCategory,
    SourceType,
    NewsSearchSchema,
)

from ..repositories import NewsRepository, NewsFilters
from ..dtos import NewsStatistics
from ..dtos import NewsStatistics


@dataclass
class NewsQueryService:
    """Encapsulates read-only news use cases."""

    session: AsyncSession

    @property
    def repo(self) -> NewsRepository:
        return NewsRepository(self.session)

    async def get_by_url(self, url: str) -> Optional[NewsItem]:
        return await self.repo.fetch_by_url(url)

    async def get_news_item(
        self,
        news_id: str,
        *,
        include_relations: bool = False,
    ) -> Optional[NewsItem]:
        return await self.repo.fetch_by_id(news_id, include_relations=include_relations)

    async def list_news(
        self,
        *,
        category: Optional[NewsCategory] = None,
        company_id: Optional[str] = None,
        company_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,  # For optimized JOIN filtering
        include_global_companies: bool = True,
        limit: int = 20,
        offset: int = 0,
        search_query: Optional[str] = None,
        source_type: Optional[SourceType] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_priority: Optional[float] = None,
    ) -> Tuple[List[NewsItem], int]:
        from uuid import UUID
        
        # Convert user_id string to UUID if provided
        user_id_uuid = None
        if user_id:
            try:
                user_id_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            except (ValueError, TypeError):
                user_id_uuid = None
        
        filters = NewsFilters(
            category=category,
            company_id=company_id,
            company_ids=company_ids,
            user_id=user_id_uuid,
            include_global_companies=include_global_companies,
            limit=limit,
            offset=offset,
            search_query=search_query,
            source_type=source_type,
            start_date=start_date,
            end_date=end_date,
            min_priority=min_priority,
        )
        return await self.repo.list_news(filters)

    async def search_news(
        self,
        search_params: NewsSearchSchema,
    ) -> Tuple[List[NewsItem], int]:
        return await self.list_news(
            category=search_params.category,
            company_id=search_params.company_id,
            limit=search_params.limit,
            offset=search_params.offset,
            search_query=search_params.query,
            source_type=search_params.source_type,
            start_date=search_params.start_date,
            end_date=search_params.end_date,
        )

    async def get_statistics(self) -> NewsStatistics:
        return await self.repo.aggregate_statistics()

    async def get_statistics_for_companies(
        self,
        company_ids: List[str],
    ) -> NewsStatistics:
        return await self.repo.aggregate_statistics_for_companies(company_ids)

    async def get_category_statistics(
        self,
        category: NewsCategory,
        company_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return await self.repo.category_statistics(category, company_ids)

    async def count_news(
        self,
        *,
        category: Optional[NewsCategory] = None,
        company_id: Optional[str] = None,
        company_ids: Optional[List[str]] = None,
    ) -> int:
        filters = NewsFilters(
            category=category,
            company_id=company_id,
            company_ids=company_ids,
        )
        return await self.repo.count_news(filters)

    async def fetch_recent(
        self,
        hours: int = 24,
        limit: int = 10,
    ) -> List[NewsItem]:
        return await self.repo.fetch_recent(hours=hours, limit=limit)

    async def get_statistics(self) -> NewsStatistics:
        return await self.repo.aggregate_statistics()

    async def get_statistics_for_companies(
        self, company_ids: List[str]
    ) -> NewsStatistics:
        return await self.repo.aggregate_statistics_for_companies(company_ids)

    async def count_news(
        self,
        *,
        category: Optional[NewsCategory] = None,
        company_id: Optional[str] = None,
        company_ids: Optional[List[str]] = None,
    ) -> int:
        filters = NewsFilters(
            category=category,
            company_id=company_id,
            company_ids=company_ids,
        )
        return await self.repo.count_news(filters)

    async def fetch_recent(self, hours: int = 24, limit: int = 10) -> List[NewsItem]:
        return await self.repo.fetch_recent(hours=hours, limit=limit)


