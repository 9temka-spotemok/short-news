"""
Competitor analysis service
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from loguru import logger
import uuid

from app.models import NewsItem, Company, CompetitorComparison


class CompetitorAnalysisService:
    """Service for competitor analysis and comparison"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def compare_companies(
        self,
        company_ids: List[str],
        date_from: datetime,
        date_to: datetime,
        user_id: Optional[str] = None,
        comparison_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple companies
        
        Args:
            company_ids: List of company IDs to compare
            date_from: Start date
            date_to: End date
            user_id: User ID (for saving comparison)
            comparison_name: Optional name for the comparison
            
        Returns:
            Comparison data
        """
        logger.info(f"Comparing {len(company_ids)} companies from {date_from} to {date_to}")
        
        # Get company info
        companies = await self._get_companies(company_ids)
        
        # Calculate metrics for each company
        metrics = {
            "news_volume": {},
            "category_distribution": {},
            "activity_score": {},
            "daily_activity": {},
            "top_news": {}
        }
        
        for company_id in company_ids:
            company_uuid = uuid.UUID(company_id)
            
            # News volume
            metrics["news_volume"][company_id] = await self.get_news_volume(
                company_uuid, date_from, date_to
            )
            
            # Category distribution
            metrics["category_distribution"][company_id] = await self.get_category_distribution(
                company_uuid, date_from, date_to
            )
            
            # Activity score
            metrics["activity_score"][company_id] = await self.get_activity_score(
                company_uuid, date_from, date_to
            )
            
            # Daily activity
            metrics["daily_activity"][company_id] = await self.get_daily_activity(
                company_uuid, date_from, date_to
            )
            
            # Top news
            metrics["top_news"][company_id] = await self.get_top_news(
                company_uuid, date_from, date_to, limit=5
            )
        
        comparison_data = {
            "companies": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "logo_url": c.logo_url,
                    "category": c.category
                }
                for c in companies
            ],
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "metrics": metrics
        }
        
        # Save comparison if user_id provided
        if user_id:
            await self._save_comparison(
                user_id, company_ids, date_from, date_to, comparison_name, metrics
            )
        
        return comparison_data
    
    async def get_news_volume(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime
    ) -> int:
        """Get total news volume for a company"""
        result = await self.db.execute(
            select(func.count(NewsItem.id))
            .where(
                and_(
                    NewsItem.company_id == company_id,
                    NewsItem.published_at >= date_from,
                    NewsItem.published_at <= date_to
                )
            )
        )
        return result.scalar() or 0
    
    async def get_category_distribution(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime
    ) -> Dict[str, int]:
        """Get category distribution for a company"""
        result = await self.db.execute(
            select(NewsItem.category, func.count(NewsItem.id).label('count'))
            .where(
                and_(
                    NewsItem.company_id == company_id,
                    NewsItem.published_at >= date_from,
                    NewsItem.published_at <= date_to
                )
            )
            .group_by(NewsItem.category)
        )
        
        distribution = {}
        for category, count in result.all():
            if category:
                distribution[category] = count
        
        return distribution
    
    async def get_activity_score(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime
    ) -> float:
        """
        Calculate activity score for a company
        
        Score is based on:
        - News volume (weighted)
        - Category diversity
        - Recency of news
        """
        # Get news items
        result = await self.db.execute(
            select(NewsItem)
            .where(
                and_(
                    NewsItem.company_id == company_id,
                    NewsItem.published_at >= date_from,
                    NewsItem.published_at <= date_to
                )
            )
        )
        news_items = result.scalars().all()
        
        if not news_items:
            return 0.0
        
        # Volume score (normalized to 0-40 points)
        volume = len(news_items)
        volume_score = min(volume * 2, 40)
        
        # Category diversity score (0-30 points)
        categories = set(item.category for item in news_items if item.category)
        diversity_score = min(len(categories) * 3, 30)
        
        # Recency score (0-30 points)
        now = datetime.utcnow()
        days_range = (date_to - date_from).days or 1
        recent_news = sum(1 for item in news_items if (now - item.published_at).days <= days_range / 2)
        recency_score = min((recent_news / volume) * 30, 30) if volume > 0 else 0
        
        total_score = volume_score + diversity_score + recency_score
        
        return round(total_score, 2)
    
    async def get_daily_activity(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime
    ) -> Dict[str, int]:
        """Get daily activity breakdown"""
        result = await self.db.execute(
            select(
                func.date(NewsItem.published_at).label('date'),
                func.count(NewsItem.id).label('count')
            )
            .where(
                and_(
                    NewsItem.company_id == company_id,
                    NewsItem.published_at >= date_from,
                    NewsItem.published_at <= date_to
                )
            )
            .group_by(func.date(NewsItem.published_at))
            .order_by(func.date(NewsItem.published_at))
        )
        
        daily_data = {}
        for date, count in result.all():
            daily_data[str(date)] = count
        
        return daily_data
    
    async def get_top_news(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get top news items for a company"""
        result = await self.db.execute(
            select(NewsItem)
            .where(
                and_(
                    NewsItem.company_id == company_id,
                    NewsItem.published_at >= date_from,
                    NewsItem.published_at <= date_to
                )
            )
            .order_by(desc(NewsItem.priority_score), desc(NewsItem.published_at))
            .limit(limit)
        )
        
        news_items = result.scalars().all()
        
        return [
            {
                "id": str(item.id),
                "title": item.title,
                "category": item.category,
                "published_at": item.published_at.isoformat(),
                "source_url": item.source_url,
                "priority_score": item.priority_score
            }
            for item in news_items
        ]
    
    async def _get_companies(self, company_ids: List[str]) -> List[Company]:
        """Get company objects"""
        uuids = [uuid.UUID(cid) for cid in company_ids]
        result = await self.db.execute(
            select(Company).where(Company.id.in_(uuids))
        )
        return list(result.scalars().all())
    
    async def _save_comparison(
        self,
        user_id: str,
        company_ids: List[str],
        date_from: datetime,
        date_to: datetime,
        name: Optional[str],
        metrics: Dict[str, Any]
    ) -> CompetitorComparison:
        """Save comparison to database"""
        try:
            comparison = CompetitorComparison(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                company_ids=[uuid.UUID(cid) for cid in company_ids],
                date_from=date_from,
                date_to=date_to,
                name=name or f"Comparison {datetime.utcnow().strftime('%Y-%m-%d')}",
                metrics=metrics
            )
            
            self.db.add(comparison)
            await self.db.commit()
            await self.db.refresh(comparison)
            
            logger.info(f"Comparison saved: {comparison.id}")
            return comparison
            
        except Exception as e:
            logger.error(f"Error saving comparison: {e}")
            await self.db.rollback()
            raise
    
    async def get_user_comparisons(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's saved comparisons"""
        result = await self.db.execute(
            select(CompetitorComparison)
            .where(CompetitorComparison.user_id == uuid.UUID(user_id))
            .order_by(desc(CompetitorComparison.created_at))
            .limit(limit)
        )
        
        comparisons = result.scalars().all()
        
        return [
            {
                "id": str(c.id),
                "name": c.name,
                "company_ids": [str(cid) for cid in c.company_ids],
                "date_from": c.date_from.isoformat(),
                "date_to": c.date_to.isoformat(),
                "created_at": c.created_at.isoformat()
            }
            for c in comparisons
        ]
    
    async def get_comparison(self, comparison_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get specific comparison"""
        result = await self.db.execute(
            select(CompetitorComparison)
            .where(
                and_(
                    CompetitorComparison.id == uuid.UUID(comparison_id),
                    CompetitorComparison.user_id == uuid.UUID(user_id)
                )
            )
        )
        
        comparison = result.scalar_one_or_none()
        if not comparison:
            return None
        
        # Get company info
        companies = await self._get_companies([str(cid) for cid in comparison.company_ids])
        
        return {
            "id": str(comparison.id),
            "name": comparison.name,
            "companies": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "logo_url": c.logo_url
                }
                for c in companies
            ],
            "date_from": comparison.date_from.isoformat(),
            "date_to": comparison.date_to.isoformat(),
            "metrics": comparison.metrics,
            "created_at": comparison.created_at.isoformat()
        }
    
    async def delete_comparison(self, comparison_id: str, user_id: str) -> bool:
        """Delete comparison"""
        try:
            result = await self.db.execute(
                select(CompetitorComparison)
                .where(
                    and_(
                        CompetitorComparison.id == uuid.UUID(comparison_id),
                        CompetitorComparison.user_id == uuid.UUID(user_id)
                    )
                )
            )
            
            comparison = result.scalar_one_or_none()
            if comparison:
                await self.db.delete(comparison)
                await self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting comparison: {e}")
            await self.db.rollback()
            return False

