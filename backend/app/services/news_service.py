"""
News service for managing news items
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from loguru import logger

from app.models.news import NewsItem, NewsCategory, SourceType
from app.models.company import Company


class NewsService:
    """Service for managing news items"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_news_item(self, news_data: Dict[str, Any]) -> NewsItem:
        """
        Create a new news item
        """
        try:
            # Check if news item already exists
            existing = await self.get_news_by_url(news_data['source_url'])
            if existing:
                logger.info(f"News item already exists: {news_data['source_url']}")
                return existing
            
            # Coerce enums if provided as strings (common when coming from scrapers)
            if 'source_type' in news_data and isinstance(news_data['source_type'], str):
                try:
                    news_data['source_type'] = SourceType(news_data['source_type'])
                except ValueError:
                    logger.warning(f"Unknown source_type '{news_data['source_type']}', defaulting to BLOG")
                    news_data['source_type'] = SourceType.BLOG

            if 'category' in news_data and isinstance(news_data['category'], str):
                try:
                    news_data['category'] = NewsCategory(news_data['category'])
                except ValueError:
                    # Leave category unset if unknown
                    news_data.pop('category', None)

            # Resolve company ID if company name is provided
            if 'company_id' in news_data and isinstance(news_data['company_id'], str):
                company = await self.get_company_by_name(news_data['company_id'])
                if company:
                    news_data['company_id'] = company.id
            
            # Create news item
            news_item = NewsItem(**news_data)
            self.db.add(news_item)
            await self.db.commit()
            await self.db.refresh(news_item)
            
            logger.info(f"Created news item: {news_item.title[:50]}...")
            return news_item
            
        except Exception as e:
            logger.error(f"Failed to create news item: {e}")
            await self.db.rollback()
            raise
    
    async def get_news_by_url(self, url: str) -> Optional[NewsItem]:
        """
        Get news item by source URL
        """
        try:
            result = await self.db.execute(
                select(NewsItem).where(NewsItem.source_url == url)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get news by URL: {e}")
            return None
    
    async def get_news_items(
        self,
        category: Optional[str] = None,
        company_id: Optional[str] = None,
        company_ids: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
        search_query: Optional[str] = None
    ) -> List[NewsItem]:
        """
        Get news items with filtering and pagination
        """
        try:
            from sqlalchemy.orm import selectinload
            
            query = select(NewsItem).options(selectinload(NewsItem.company))
            
            # Apply filters
            if category:
                # Category is now a string, not enum
                query = query.where(NewsItem.category == category)
            
            if company_ids:
                query = query.where(NewsItem.company_id.in_(company_ids))
            elif company_id:
                query = query.where(NewsItem.company_id == company_id)
            
            if search_query:
                like = f"%{search_query}%"
                query = query.where(
                    or_(
                        NewsItem.title.ilike(like),
                        NewsItem.content.ilike(like),
                        NewsItem.summary.ilike(like)
                    )
                )
            
            # Order by published date (newest first)
            query = query.order_by(desc(NewsItem.published_at))
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get news items: {e}")
            return []
    
    async def get_news_item_by_id(self, news_id: str) -> Optional[NewsItem]:
        """
        Get news item by ID
        """
        try:
            result = await self.db.execute(
                select(NewsItem).where(NewsItem.id == news_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get news item by ID: {e}")
            return None
    
    async def search_news(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[NewsItem]:
        """
        Search news items by text query
        """
        try:
            # Use full-text search if available
            # Use concatenation via func.concat for cross-DB safety
            ts_vector = func.to_tsvector(
                'english',
                func.concat(func.coalesce(NewsItem.title, ''), ' ', func.coalesce(NewsItem.content, ''))
            )
            search_stmt = (
                select(NewsItem)
                .where(ts_vector.match(query))
                .order_by(desc(NewsItem.published_at))
                .offset(offset)
                .limit(limit)
            )
            
            result = await self.db.execute(search_stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to search news: {e}")
            # Fallback to simple text search
            return await self.get_news_items(
                search_query=query,
                limit=limit,
                offset=offset
            )
    
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
