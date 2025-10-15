"""
Enhanced News service with improved architecture and error handling
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, distinct, case
from sqlalchemy.orm import selectinload
from loguru import logger
from uuid import UUID

from app.models.news import (
    NewsItem, NewsCategory, SourceType, 
    NewsCreateSchema, NewsUpdateSchema, NewsSearchSchema, NewsStatsSchema
)
from app.models.company import Company
from app.core.exceptions import NewsServiceError, ValidationError, NotFoundError


class NewsService:
    """Enhanced service for managing news items with improved error handling"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: Dict[str, Any] = {}
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if exc_type:
            await self.db.rollback()
        else:
            await self.db.commit()
    
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
            # Validate input data
            validated_data = await self._validate_news_data(news_data)
            
            # Check if news item already exists
            existing = await self.get_news_by_url(validated_data['source_url'])
            if existing:
                logger.info(f"News item already exists: {validated_data['source_url']}")
                return existing
            
            # Create news item
            news_item = NewsItem(**validated_data)
            self.db.add(news_item)
            await self.db.flush()  # Flush to get the ID
            
            # Update search vector
            await self._update_search_vector(news_item)
            
            await self.db.commit()
            await self.db.refresh(news_item)
            
            logger.info(f"Created news item: {news_item.title[:50]}...")
            return news_item
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create news item: {e}")
            await self.db.rollback()
            raise NewsServiceError(f"Failed to create news item: {str(e)}")
    
    async def _validate_news_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize news data
        
        Args:
            data: Raw news data
            
        Returns:
            Validated and normalized data
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Use Pydantic for validation
            validated = NewsCreateSchema(**data)
            result = validated.model_dump()
            
            # Coerce enums if provided as strings
            if isinstance(result.get('source_type'), str):
                try:
                    result['source_type'] = SourceType(result['source_type'])
                except ValueError:
                    logger.warning(f"Unknown source_type '{result['source_type']}', defaulting to BLOG")
                    result['source_type'] = SourceType.BLOG

            if isinstance(result.get('category'), str):
                try:
                    result['category'] = NewsCategory(result['category'])
                except ValueError:
                    result.pop('category', None)

            # Resolve company ID if company name is provided
            if result.get('company_id') and isinstance(result['company_id'], str):
                company = await self.get_company_by_name(result['company_id'])
                if company:
                    result['company_id'] = company.id
                else:
                    result['company_id'] = None
            
            return result
            
        except Exception as e:
            raise ValidationError(f"Invalid news data: {str(e)}")
    
    async def _update_search_vector(self, news_item: NewsItem) -> None:
        """
        Update full-text search vector for news item
        
        Args:
            news_item: News item to update
        """
        try:
            # Create search vector from title and content
            search_text = f"{news_item.title} {news_item.content or ''} {news_item.summary or ''}"
            news_item.search_vector = func.to_tsvector('english', search_text)
        except Exception as e:
            logger.warning(f"Failed to update search vector: {e}")
    
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
            
            result = await self.db.execute(
                select(NewsItem)
                .options(selectinload(NewsItem.company))
                .where(NewsItem.source_url == url)
            )
            news_item = result.scalar_one_or_none()
            
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
            # Build base query with eager loading
            query = select(NewsItem).options(
                selectinload(NewsItem.company),
                selectinload(NewsItem.keywords)
            )
            count_query = select(func.count(NewsItem.id))
            
            # Apply filters
            filters = []
            
            if category:
                filters.append(NewsItem.category == category)
            
            if company_ids:
                filters.append(NewsItem.company_id.in_(company_ids))
            elif company_id:
                filters.append(NewsItem.company_id == company_id)
            
            if source_type:
                filters.append(NewsItem.source_type == source_type)
            
            if start_date:
                filters.append(NewsItem.published_at >= start_date)
            
            if end_date:
                filters.append(NewsItem.published_at <= end_date)
            
            if min_priority is not None:
                filters.append(NewsItem.priority_score >= min_priority)
            
            if search_query:
                # Use full-text search if available, otherwise fallback to ILIKE
                if hasattr(NewsItem, 'search_vector'):
                    filters.append(NewsItem.search_vector.match(search_query))
                else:
                    like = f"%{search_query}%"
                    filters.append(
                        or_(
                            NewsItem.title.ilike(like),
                            NewsItem.content.ilike(like),
                            NewsItem.summary.ilike(like)
                        )
                    )
            
            # Apply filters to both queries
            if filters:
                query = query.where(and_(*filters))
                count_query = count_query.where(and_(*filters))
            
            # Get total count
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Order by published date (newest first) and priority
            query = query.order_by(
                desc(NewsItem.published_at),
                desc(NewsItem.priority_score)
            )
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            result = await self.db.execute(query)
            news_items = result.scalars().all()
            
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
            # Total count
            total_count = await self.db.execute(select(func.count(NewsItem.id)))
            total_count = total_count.scalar()
            
            # Category counts
            category_counts = await self.db.execute(
                select(
                    NewsItem.category,
                    func.count(NewsItem.id).label('count')
                )
                .group_by(NewsItem.category)
            )
            category_dict = {row.category: row.count for row in category_counts}
            
            # Source type counts
            source_counts = await self.db.execute(
                select(
                    NewsItem.source_type,
                    func.count(NewsItem.id).label('count')
                )
                .group_by(NewsItem.source_type)
            )
            source_dict = {row.source_type: row.count for row in source_counts}
            
            # Recent news count (last 24 hours)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_count = await self.db.execute(
                select(func.count(NewsItem.id))
                .where(NewsItem.published_at >= recent_cutoff)
            )
            recent_count = recent_count.scalar()
            
            # High priority count
            high_priority_count = await self.db.execute(
                select(func.count(NewsItem.id))
                .where(NewsItem.priority_score >= 0.8)
            )
            high_priority_count = high_priority_count.scalar()
            
            return NewsStatsSchema(
                total_count=total_count,
                category_counts=category_dict,
                source_type_counts=source_dict,
                recent_count=recent_count,
                high_priority_count=high_priority_count
            )
            
        except Exception as e:
            logger.error(f"Failed to get news statistics: {e}")
            raise NewsServiceError(f"Failed to get statistics: {str(e)}")
    
    async def get_company_by_name(self, name: str) -> Optional[Company]:
        """
        Get company by name
        """
        try:
            result = await self.db.execute(
                select(Company).where(Company.name.ilike(f'%{name}%'))
            )
            return result.scalar_one_or_none()
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
            query = select(func.count(NewsItem.id))
            
            if category:
                # Category is now a string, not enum
                query = query.where(NewsItem.category == category)
            
            if company_ids:
                query = query.where(NewsItem.company_id.in_(company_ids))
            elif company_id:
                query = query.where(NewsItem.company_id == company_id)
            
            result = await self.db.execute(query)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Failed to get news count: {e}")
            return 0
    
    async def get_recent_news(self, hours: int = 24, limit: int = 10) -> List[NewsItem]:
        """
        Get recent news items from the last N hours
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            query = select(NewsItem).where(
                NewsItem.published_at >= cutoff_time
            ).order_by(desc(NewsItem.published_at)).limit(limit)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get recent news: {e}")
            return []
    
    async def update_news_item(self, news_id: str, update_data: Dict[str, Any]) -> Optional[NewsItem]:
        """
        Update news item
        """
        try:
            news_item = await self.get_news_item_by_id(news_id)
            if not news_item:
                return None
            
            for key, value in update_data.items():
                if hasattr(news_item, key):
                    setattr(news_item, key, value)
            
            await self.db.commit()
            await self.db.refresh(news_item)
            
            logger.info(f"Updated news item: {news_item.title[:50]}...")
            return news_item
            
        except Exception as e:
            logger.error(f"Failed to update news item: {e}")
            await self.db.rollback()
            return None
    
    async def delete_news_item(self, news_id: str) -> bool:
        """
        Delete news item
        """
        try:
            news_item = await self.get_news_item_by_id(news_id)
            if not news_item:
                return False
            
            await self.db.delete(news_item)
            await self.db.commit()
            
            logger.info(f"Deleted news item: {news_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete news item: {e}")
            await self.db.rollback()
            return False
