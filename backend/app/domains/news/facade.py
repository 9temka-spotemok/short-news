"""
News domain facade.

The facade provides a stable entry point for API layers, background tasks and
other domains to interact with news functionality without knowing about the
underlying services or repositories. Implementation is intentionally minimal
for now and will be expanded as parts of ``NewsService`` are migrated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import (
    NewsItem,
    NewsCategory,
    SourceType,
    NewsSearchSchema,
)

from .services.query_service import NewsQueryService
from .services.ingestion_service import NewsIngestionService
from .services.scraper_service import NewsScraperService
from .dtos import NewsStatistics


@dataclass
class NewsFacade:
    """Facade coordinating news services and repositories."""

    session: AsyncSession

    @property
    def query_service(self) -> NewsQueryService:
        return NewsQueryService(self.session)

    @property
    def ingestion_service(self) -> NewsIngestionService:
        return NewsIngestionService(self.session)

    @property
    def scraper_service(self) -> NewsScraperService:
        return NewsScraperService(self.session)

    async def get_by_url(self, url: str) -> Optional[NewsItem]:
        """Retrieve a news item by source URL."""
        return await self.query_service.get_by_url(url)

    async def get_news_item(
        self,
        news_id: str,
        *,
        include_relations: bool = False,
    ) -> Optional[NewsItem]:
        return await self.query_service.get_news_item(
            news_id,
            include_relations=include_relations,
        )

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
        return await self.query_service.list_news(
            category=category,
            company_id=company_id,
            company_ids=company_ids,
            user_id=user_id,
            include_global_companies=include_global_companies,
            limit=limit,
            offset=offset,
            search_query=search_query,
            source_type=source_type,
            start_date=start_date,
            end_date=end_date,
            min_priority=min_priority,
        )

    async def search_news(
        self,
        search_params: NewsSearchSchema,
    ) -> Tuple[List[NewsItem], int]:
        return await self.query_service.search_news(search_params)

    async def get_statistics(self) -> NewsStatistics:
        return await self.query_service.get_statistics()

    async def get_statistics_for_companies(
        self,
        company_ids: List[str],
    ) -> NewsStatistics:
        return await self.query_service.get_statistics_for_companies(company_ids)

    async def get_category_statistics(
        self,
        category: NewsCategory,
        company_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return await self.query_service.get_category_statistics(category, company_ids)

    async def count_news(
        self,
        *,
        category: Optional[NewsCategory] = None,
        company_id: Optional[str] = None,
        company_ids: Optional[List[str]] = None,
    ) -> int:
        return await self.query_service.count_news(
            category=category,
            company_id=company_id,
            company_ids=company_ids,
        )

    async def fetch_recent(self, hours: int = 24, limit: int = 10) -> List[NewsItem]:
        return await self.query_service.fetch_recent(hours=hours, limit=limit)

    async def create_news(self, data: Dict[str, Any]) -> NewsItem:
        return await self.ingestion_service.create_news_item(data)

    async def update_news(
        self,
        news_id: str,
        data: Dict[str, Any],
    ) -> Optional[NewsItem]:
        return await self.ingestion_service.update_news_item(news_id, data)

    async def delete_news(self, news_id: str) -> bool:
        return await self.ingestion_service.delete_news_item(news_id)

