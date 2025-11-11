"""
SQLAlchemy repository for news-related persistence operations.

This module currently hosts the first batch of queries extracted from the
legacy ``NewsService``. Additional methods will be moved here iteratively.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.news import NewsItem, NewsCategory, SourceType
from app.models.company import Company
from ..dtos import NewsStatistics


@dataclass
class NewsFilters:
    category: Optional[NewsCategory] = None
    company_id: Optional[str] = None
    company_ids: Optional[List[str]] = None
    limit: int = 20
    offset: int = 0
    search_query: Optional[str] = None
    source_type: Optional[SourceType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_priority: Optional[float] = None


class NewsRepository:
    """Encapsulates read operations for the news domain."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def fetch_by_url(self, url: str) -> Optional[NewsItem]:
        stmt = (
            select(NewsItem)
            .options(selectinload(NewsItem.company))
            .where(NewsItem.source_url == url)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def fetch_by_id(
        self,
        news_id: str,
        *,
        include_relations: bool = False,
    ) -> Optional[NewsItem]:
        stmt = select(NewsItem)
        if include_relations:
            stmt = stmt.options(
                selectinload(NewsItem.company),
                selectinload(NewsItem.keywords),
                selectinload(NewsItem.activities),
            )
        stmt = stmt.where(NewsItem.id == news_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _build_criteria(self, filters: NewsFilters) -> List:
        criteria = []

        if filters.category:
            category_value = (
                filters.category.value
                if hasattr(filters.category, "value")
                else str(filters.category)
            )
            criteria.append(NewsItem.category == category_value)

        if filters.company_ids:
            criteria.append(NewsItem.company_id.in_(filters.company_ids))
        elif filters.company_id:
            criteria.append(NewsItem.company_id == filters.company_id)

        if filters.source_type:
            source_type_value = (
                filters.source_type.value
                if hasattr(filters.source_type, "value")
                else str(filters.source_type)
            )
            criteria.append(NewsItem.source_type == source_type_value)

        if filters.start_date:
            criteria.append(NewsItem.published_at >= filters.start_date)

        if filters.end_date:
            criteria.append(NewsItem.published_at <= filters.end_date)

        if filters.min_priority is not None:
            criteria.append(NewsItem.priority_score >= filters.min_priority)

        if filters.search_query:
            like = f"%{filters.search_query}%"
            if hasattr(NewsItem, "search_vector"):
                criteria.append(NewsItem.search_vector.match(filters.search_query))
            else:
                criteria.append(
                    or_(
                        NewsItem.title.ilike(like),
                        NewsItem.content.ilike(like),
                        NewsItem.summary.ilike(like),
                    )
                )

        return criteria

    async def list_news(self, filters: NewsFilters) -> Tuple[List[NewsItem], int]:
        stmt = select(NewsItem).options(
            selectinload(NewsItem.company),
            selectinload(NewsItem.keywords),
        )
        count_stmt = select(func.count(NewsItem.id))

        criteria = self._build_criteria(filters)

        if criteria:
            stmt = stmt.where(and_(*criteria))
            count_stmt = count_stmt.where(and_(*criteria))

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(
            desc(NewsItem.published_at),
            desc(NewsItem.priority_score),
        ).offset(filters.offset).limit(filters.limit)

        result = await self._session.execute(stmt)
        return result.scalars().all(), total

    async def count_news(self, filters: Optional[NewsFilters] = None) -> int:
        stmt = select(func.count(NewsItem.id))
        if filters:
            criteria = self._build_criteria(filters)
            if criteria:
                stmt = stmt.where(and_(*criteria))
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def fetch_recent(self, hours: int = 24, limit: int = 10) -> List[NewsItem]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(NewsItem)
            .where(NewsItem.published_at >= cutoff)
            .order_by(desc(NewsItem.published_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def category_statistics(
        self,
        category: NewsCategory,
        company_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        filters = NewsFilters(
            category=category,
            company_ids=company_ids,
        )
        criteria = self._build_criteria(filters)

        stmt = select(func.count(NewsItem.id))
        if criteria:
            stmt = stmt.where(and_(*criteria))
        total_result = await self._session.execute(stmt)
        total_in_category = total_result.scalar() or 0

        top_companies_stmt = (
            select(
                Company.id,
                Company.name,
                func.count(NewsItem.id).label("count"),
            )
            .select_from(NewsItem)
            .join(Company, NewsItem.company_id == Company.id, isouter=True)
            .where(and_(*criteria))
            .group_by(Company.id, Company.name)
            .order_by(desc("count"))
            .limit(5)
        )
        top_companies_result = await self._session.execute(top_companies_stmt)
        top_companies = []
        for company_id, company_name, count in top_companies_result:
            top_companies.append({
                "company_id": str(company_id) if company_id else None,
                "name": company_name,
                "count": count,
            })

        source_stmt = (
            select(NewsItem.source_type, func.count(NewsItem.id).label("count"))
            .where(and_(*criteria))
            .group_by(NewsItem.source_type)
        )
        source_rows = await self._session.execute(source_stmt)
        source_distribution = {
            str(row[0]): row[1]
            for row in source_rows
            if row[0]
        }

        return {
            "top_companies": top_companies,
            "source_distribution": source_distribution,
            "total_in_category": total_in_category,
        }

    async def aggregate_statistics(self) -> NewsStatistics:
        total_result = await self._session.execute(select(func.count(NewsItem.id)))
        total_count = total_result.scalar() or 0

        category_rows = await self._session.execute(
            select(NewsItem.category, func.count(NewsItem.id))
            .group_by(NewsItem.category)
        )
        category_counts = {
            str(row[0]): row[1]
            for row in category_rows
            if row[0]
        }

        source_rows = await self._session.execute(
            select(NewsItem.source_type, func.count(NewsItem.id))
            .group_by(NewsItem.source_type)
        )
        source_counts = {
            str(row[0]): row[1]
            for row in source_rows
            if row[0]
        }

        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_result = await self._session.execute(
            select(func.count(NewsItem.id)).where(NewsItem.published_at >= recent_cutoff)
        )
        recent_count = recent_result.scalar() or 0

        high_priority_result = await self._session.execute(
            select(func.count(NewsItem.id)).where(NewsItem.priority_score >= 0.8)
        )
        high_priority_count = high_priority_result.scalar() or 0

        return NewsStatistics(
            total_count=total_count,
            category_counts=category_counts,
            source_counts=source_counts,
            recent_count=recent_count,
            high_priority_count=high_priority_count,
        )

    async def aggregate_statistics_for_companies(
        self, company_ids: List[str]
    ) -> NewsStatistics:
        id_filter = NewsItem.company_id.in_(company_ids)

        total_result = await self._session.execute(
            select(func.count(NewsItem.id)).where(id_filter)
        )
        total_count = total_result.scalar() or 0

        category_rows = await self._session.execute(
            select(NewsItem.category, func.count(NewsItem.id))
            .where(id_filter)
            .group_by(NewsItem.category)
        )
        category_counts = {
            str(row[0]): row[1]
            for row in category_rows
            if row[0]
        }

        source_rows = await self._session.execute(
            select(NewsItem.source_type, func.count(NewsItem.id))
            .where(id_filter)
            .group_by(NewsItem.source_type)
        )
        source_counts = {
            str(row[0]): row[1]
            for row in source_rows
            if row[0]
        }

        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_result = await self._session.execute(
            select(func.count(NewsItem.id)).where(
                id_filter,
                NewsItem.published_at >= recent_cutoff,
            )
        )
        recent_count = recent_result.scalar() or 0

        high_priority_result = await self._session.execute(
            select(func.count(NewsItem.id)).where(
                id_filter,
                NewsItem.priority_score >= 0.8,
            )
        )
        high_priority_count = high_priority_result.scalar() or 0

        return NewsStatistics(
            total_count=total_count,
            category_counts=category_counts,
            source_counts=source_counts,
            recent_count=recent_count,
            high_priority_count=high_priority_count,
        )



