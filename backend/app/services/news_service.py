"""
Enhanced News service with improved architecture and error handling
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger
from uuid import UUID

from app.domains.news.repositories import (
    NewsRepository,
    NewsFilters,
    CompanyRepository,
)
from app.domains.news.services.ingestion_service import NewsIngestionService
from app.models.news import (
    NewsItem,
    NewsCategory,
    SourceType,
    NewsUpdateSchema,
    NewsSearchSchema,
    NewsStatsSchema,
)
from app.models.company import Company
from app.core.exceptions import NewsServiceError, ValidationError, NotFoundError


class NewsService:
    """Enhanced service for managing news items with improved error handling"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: Dict[str, Any] = {}
        self._repo = NewsRepository(db)
        self._company_repo = CompanyRepository(db)
        self._ingestion = NewsIngestionService(db)

    async def create_news_item(self, news_data: Dict[str, Any]) -> NewsItem:
        """
        Create a new news item with enhanced validation and error handling
        
        Args:
            news_data: Dictionary containing news item data
            
        Returns:
            Created NewsItem instance
            
        Raises:
            ValidationError: If input data is invalid
            NewsServiceError: If creation fails
        """
        try:
            news_item = await self._ingestion.create_news_item(news_data)
            cache_key = f"news_url:{news_item.source_url}"
            self._cache[cache_key] = news_item
            logger.info(f"Created news item: {news_item.title[:50]}...")
            return news_item
        except (ValidationError, NewsServiceError):
            raise
        except Exception as e:
            logger.error(f"Failed to create news item: {e}")
            raise NewsServiceError(f"Failed to create news item: {str(e)}")
    
    async def get_news_by_url(self, url: str) -> Optional[NewsItem]:
        """
        Get news item by source URL with caching
        
        Args:
            url: Source URL to search for
            
        Returns:
            NewsItem if found, None otherwise
        """
        try:
            # Check cache first
            cache_key = f"news_url:{url}"
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            news_item = await self._repo.fetch_by_url(url)
            
            # Cache result
            if news_item:
                self._cache[cache_key] = news_item
            
            return news_item
            
        except Exception as e:
            logger.error(f"Failed to get news by URL: {e}")
            return None
    
    async def get_news_items(
        self,
        category: Optional[NewsCategory] = None,
        company_id: Optional[str] = None,
        company_ids: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
        search_query: Optional[str] = None,
        source_type: Optional[SourceType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_priority: Optional[float] = None
    ) -> Tuple[List[NewsItem], int]:
        """
        Get news items with enhanced filtering and pagination
        
        Args:
            category: Filter by news category
            company_id: Filter by single company ID
            company_ids: Filter by multiple company IDs
            limit: Maximum number of results
            offset: Number of results to skip
            search_query: Text search query
            source_type: Filter by source type
            start_date: Filter by start date
            end_date: Filter by end date
            min_priority: Minimum priority score
            
        Returns:
            Tuple of (news items list, total count)
        """
        try:
            repo_filters = NewsFilters(
                category=category,
                company_id=company_id,
                company_ids=company_ids,
                limit=limit,
                offset=offset,
                search_query=search_query,
                source_type=source_type,
                start_date=start_date,
                end_date=end_date,
                min_priority=min_priority,
            )

            news_items, total_count = await self._repo.list_news(repo_filters)

            logger.info(f"Retrieved {len(news_items)} news items (total: {total_count})")
            return news_items, total_count
            
        except Exception as e:
            logger.error(f"Failed to get news items: {e}")
            raise NewsServiceError(f"Failed to retrieve news items: {str(e)}")
    
    async def get_news_item_by_id(self, news_id: str) -> Optional[NewsItem]:
        """
        Get news item by ID with enhanced loading
        
        Args:
            news_id: News item ID
            
        Returns:
            NewsItem if found, None otherwise
        """
        try:
            # Validate UUID format
            try:
                UUID(news_id)
            except ValueError:
                raise ValidationError(f"Invalid news ID format: {news_id}")
            
            result = await self.db.execute(
                select(NewsItem)
                .options(
                    selectinload(NewsItem.company),
                    selectinload(NewsItem.keywords),
                    selectinload(NewsItem.activities)
                )
                .where(NewsItem.id == news_id)
            )
            return result.scalar_one_or_none()
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to get news item by ID: {e}")
            return None
    
    async def search_news(
        self,
        search_params: NewsSearchSchema
    ) -> Tuple[List[NewsItem], int]:
        """
        Enhanced search news items with full-text search
        
        Args:
            search_params: Search parameters
            
        Returns:
            Tuple of (news items list, total count)
        """
        try:
            return await self.get_news_items(
                search_query=search_params.query,
                category=search_params.category,
                source_type=search_params.source_type,
                company_id=search_params.company_id,
                start_date=search_params.start_date,
                end_date=search_params.end_date,
                limit=search_params.limit,
                offset=search_params.offset
            )
            
        except Exception as e:
            logger.error(f"Failed to search news: {e}")
            raise NewsServiceError(f"Failed to search news: {str(e)}")
    
    async def get_news_statistics(self) -> NewsStatsSchema:
        """
        Get comprehensive news statistics
        
        Returns:
            NewsStatsSchema with statistics
        """
        try:
            stats = await self._repo.aggregate_statistics()
            
            return NewsStatsSchema(
                total_count=stats.total_count,
                category_counts=stats.category_counts,
                source_type_counts=stats.source_type_counts,
                recent_count=stats.recent_count,
                high_priority_count=stats.high_priority_count
            )
            
        except Exception as e:
            logger.error(f"Failed to get news statistics: {e}")
            raise NewsServiceError(f"Failed to get statistics: {str(e)}")
    
    async def get_news_statistics_by_companies(self, company_ids: List[str]) -> NewsStatsSchema:
        """
        Get comprehensive news statistics filtered by company IDs
        
        Args:
            company_ids: List of company IDs to filter by
            
        Returns:
            NewsStatsSchema with statistics filtered by companies
        """
        try:
            stats = await self._repo.aggregate_statistics_for_companies(company_ids)
            
            return NewsStatsSchema(
                total_count=stats.total_count,
                category_counts=stats.category_counts,
                source_type_counts=stats.source_type_counts,
                recent_count=stats.recent_count,
                high_priority_count=stats.high_priority_count
            )
            
        except Exception as e:
            logger.error(f"Failed to get news statistics by companies: {e}")
            raise NewsServiceError(f"Failed to get statistics by companies: {str(e)}")
    
    async def get_company_by_name(self, name: str) -> Optional[Company]:
        """
        Get company by name
        """
        try:
            return await self._company_repo.fetch_by_name(name)
        except Exception as e:
            logger.error(f"Failed to get company by name: {e}")
            return None
    
    async def get_news_count(
        self,
        category: Optional[str] = None,
        company_id: Optional[str] = None,
        company_ids: Optional[List[str]] = None
    ) -> int:
        """
        Get total count of news items
        """
        try:
            category_enum = None
            if category:
                try:
                    category_enum = NewsCategory(category)
                except ValueError:
                    logger.warning(f"Unknown category '{category}' provided to get_news_count")

            filters = NewsFilters(
                category=category_enum,
                company_id=company_id,
                company_ids=company_ids,
            )
            return await self._repo.count_news(filters)
            
        except Exception as e:
            logger.error(f"Failed to get news count: {e}")
            return 0
    
    async def get_recent_news(self, hours: int = 24, limit: int = 10) -> List[NewsItem]:
        """
        Get recent news items from the last N hours
        """
        try:
            return await self._repo.fetch_recent(hours=hours, limit=limit)
            
        except Exception as e:
            logger.error(f"Failed to get recent news: {e}")
            return []
    
    async def update_news_item(self, news_id: str, update_data: Dict[str, Any]) -> Optional[NewsItem]:
        """
        Update news item
        """
        try:
            news_item = await self._ingestion.update_news_item(news_id, update_data)
            if news_item:
                logger.info(f"Updated news item: {news_item.title[:50]}...")
            return news_item
        except NewsServiceError as e:
            logger.error(str(e))
            return None
    
    async def delete_news_item(self, news_id: str) -> bool:
        """
        Delete news item
        """
        try:
            success = await self._ingestion.delete_news_item(news_id)
            if success:
                logger.info(f"Deleted news item: {news_id}")
            return success
        except NewsServiceError as e:
            logger.error(str(e))
            return False
    
    async def get_category_statistics(self, category: NewsCategory, company_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get statistics for a specific category
        
        Args:
            category: News category to get statistics for
            company_ids: Optional list of company IDs to filter by
            
        Returns:
            Dictionary with category statistics
        """
        try:
            stats = await self._repo.category_statistics(category, company_ids)
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get category statistics: {e}")
            return {
                "top_companies": [],
                "source_distribution": {},
                "total_in_category": 0
            }