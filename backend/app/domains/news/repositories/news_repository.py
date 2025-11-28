"""
SQLAlchemy repository for news-related persistence operations.

This module currently hosts the first batch of queries extracted from the
legacy ``NewsService``. Additional methods will be moved here iteratively.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID

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
    user_id: Optional[UUID] = None  # For optimized JOIN filtering
    include_global_companies: bool = True  # Include global companies when filtering by user_id
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
        news_id: UUID | str,
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
        target_id = news_id
        if isinstance(news_id, str):
            try:
                target_id = UUID(news_id)
            except ValueError:
                target_id = news_id
        stmt = stmt.where(NewsItem.id == target_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _build_criteria(self, filters: NewsFilters) -> List:
        criteria = []

        bind = getattr(self._session, "bind", None)
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        supports_full_text = bool(
            dialect_name and dialect_name.lower().startswith("postgres")
        )

        if filters.category:
            category_value = (
                filters.category.value
                if hasattr(filters.category, "value")
                else str(filters.category)
            )
            criteria.append(NewsItem.category == category_value)

        if filters.company_ids:
            # Валидация: проверяем что список не пустой
            if not filters.company_ids:
                # Пустой список - не добавляем фильтр (вернет пустой результат)
                pass
            else:
                # КРИТИЧЕСКИ ВАЖНО: Конвертируем строки в UUID для правильного сравнения
                uuid_ids = []
                for cid in filters.company_ids:
                    if not cid:  # Пропускаем пустые строки
                        continue
                    try:
                        uuid_ids.append(UUID(cid) if isinstance(cid, str) else cid)
                    except (ValueError, TypeError):
                        # Пропускаем невалидные UUID
                        continue
                if uuid_ids:
                    criteria.append(NewsItem.company_id.in_(uuid_ids))
        elif filters.company_id:
            # Конвертируем строку в UUID если нужно
            try:
                company_id_uuid = UUID(filters.company_id) if isinstance(filters.company_id, str) else filters.company_id
                criteria.append(NewsItem.company_id == company_id_uuid)
            except (ValueError, TypeError):
                # Невалидный UUID - не добавляем фильтр
                pass

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
            if supports_full_text and hasattr(NewsItem, "search_vector"):
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
        """
        List news items with filtering.
        
        If user_id is provided, uses optimized JOIN query instead of IN clause.
        Otherwise, uses standard filtering with IN clause for company_ids.
        """
        # If user_id is provided, use optimized JOIN method
        if filters.user_id is not None:
            return await self.list_news_by_user_id(
                user_id=filters.user_id,
                filters=filters,
                include_global=filters.include_global_companies
            )
        
        # Standard filtering with IN clause (backward compatible)
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

    async def list_news_by_user_id(
        self,
        user_id: UUID,
        filters: NewsFilters,
        include_global: bool = True,
    ) -> Tuple[List[NewsItem], int]:
        """
        Optimized method to list news items filtered by user_id using JOIN.
        
        This method uses JOIN instead of IN clause for better performance,
        especially when user has many companies.
        
        Args:
            user_id: User UUID to filter companies by
            filters: NewsFilters with additional filters (category, search, etc.)
            include_global: If True, also include news from global companies (user_id IS NULL)
            
        Returns:
            Tuple of (news items list, total count)
        """
        # Build base query with JOIN for user_id filtering
        stmt = (
            select(NewsItem)
            .join(Company, NewsItem.company_id == Company.id)
            .options(
                selectinload(NewsItem.company),
                selectinload(NewsItem.keywords),
            )
        )
        
        count_stmt = (
            select(func.count(NewsItem.id))
            .join(Company, NewsItem.company_id == Company.id)
        )
        
        # Filter by user_id using JOIN (optimized)
        if include_global:
            # Include user's companies and global companies
            user_filter = or_(
                Company.user_id == user_id,
                Company.user_id.is_(None)  # Global companies
            )
        else:
            # Only user's companies
            user_filter = Company.user_id == user_id
        
        stmt = stmt.where(user_filter)
        count_stmt = count_stmt.where(user_filter)
        
        # Apply additional filters
        # Если передан company_id/company_ids - используем как дополнительный фильтр (пересечение)
        other_criteria = []
        
        # Дополнительная фильтрация по company_id/company_ids (пересечение с user_id)
        if filters.company_ids:
            # Валидация: проверяем что список не пустой
            if filters.company_ids:
                # КРИТИЧЕСКИ ВАЖНО: Конвертируем строки в UUID для правильного сравнения
                uuid_ids = []
                for cid in filters.company_ids:
                    if not cid:  # Пропускаем пустые строки
                        continue
                    try:
                        uuid_ids.append(UUID(cid) if isinstance(cid, str) else cid)
                    except (ValueError, TypeError):
                        # Пропускаем невалидные UUID
                        continue
                if uuid_ids:
                    # Дополнительная фильтрация: только компании из списка (пересечение)
                    other_criteria.append(NewsItem.company_id.in_(uuid_ids))
        elif filters.company_id:
            # Конвертируем строку в UUID если нужно
            try:
                company_id_uuid = UUID(filters.company_id) if isinstance(filters.company_id, str) else filters.company_id
                other_criteria.append(NewsItem.company_id == company_id_uuid)
            except (ValueError, TypeError):
                # Невалидный UUID - не добавляем фильтр
                pass
        
        bind = getattr(self._session, "bind", None)
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        supports_full_text = bool(
            dialect_name and dialect_name.lower().startswith("postgres")
        )
        
        if filters.category:
            category_value = (
                filters.category.value
                if hasattr(filters.category, "value")
                else str(filters.category)
            )
            other_criteria.append(NewsItem.category == category_value)
        
        if filters.source_type:
            source_type_value = (
                filters.source_type.value
                if hasattr(filters.source_type, "value")
                else str(filters.source_type)
            )
            other_criteria.append(NewsItem.source_type == source_type_value)
        
        if filters.start_date:
            other_criteria.append(NewsItem.published_at >= filters.start_date)
        
        if filters.end_date:
            other_criteria.append(NewsItem.published_at <= filters.end_date)
        
        if filters.min_priority is not None:
            other_criteria.append(NewsItem.priority_score >= filters.min_priority)
        
        if filters.search_query:
            like = f"%{filters.search_query}%"
            if supports_full_text and hasattr(NewsItem, "search_vector"):
                other_criteria.append(NewsItem.search_vector.match(filters.search_query))
            else:
                other_criteria.append(
                    or_(
                        NewsItem.title.ilike(like),
                        NewsItem.content.ilike(like),
                        NewsItem.summary.ilike(like),
                    )
                )
        
        if other_criteria:
            stmt = stmt.where(and_(*other_criteria))
            count_stmt = count_stmt.where(and_(*other_criteria))
        
        # Get total count
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Apply ordering, offset, and limit
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
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).replace(tzinfo=None)
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
        source_type_counts = {
            str(row[0]): row[1]
            for row in source_rows
            if row[0]
        }

        recent_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).replace(tzinfo=None)
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
            source_type_counts=source_type_counts,
            recent_count=recent_count,
            high_priority_count=high_priority_count,
        )

    async def aggregate_statistics_for_companies(
        self, 
        company_ids: List[str],
        user_id: Optional[UUID] = None,
        include_global: bool = True,
    ) -> NewsStatistics:
        """
        Aggregate statistics for companies.
        
        If user_id is provided, uses optimized JOIN query instead of IN clause.
        Otherwise, uses IN clause for backward compatibility.
        """
        # Если user_id указан, используем оптимизированный JOIN
        if user_id is not None:
            return await self._aggregate_statistics_by_user_id(
                user_id=user_id,
                include_global=include_global
            )
        
        # Валидация: проверяем что список не пустой
        if not company_ids:
            return NewsStatistics(
                total_count=0,
                category_counts={},
                source_type_counts={},
                recent_count=0,
                high_priority_count=0,
            )
        
        # КРИТИЧЕСКИ ВАЖНО: Конвертируем строки в UUID
        # SQLAlchemy требует UUID объекты для сравнения с UUID колонкой
        uuid_ids = []
        for cid in company_ids:
            if not cid:  # Пропускаем пустые строки
                continue
            try:
                uuid_ids.append(UUID(cid) if isinstance(cid, str) else cid)
            except (ValueError, TypeError):
                # Пропускаем невалидные UUID
                continue
        
        if not uuid_ids:
            # Возвращаем пустую статистику если нет валидных UUID
            return NewsStatistics(
                total_count=0,
                category_counts={},
                source_type_counts={},
                recent_count=0,
                high_priority_count=0,
            )
        
        id_filter = NewsItem.company_id.in_(uuid_ids)

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
        source_type_counts = {
            str(row[0]): row[1]
            for row in source_rows
            if row[0]
        }

        recent_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).replace(tzinfo=None)
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
            source_type_counts=source_type_counts,
            recent_count=recent_count,
            high_priority_count=high_priority_count,
        )

    async def _aggregate_statistics_by_user_id(
        self,
        user_id: UUID,
        include_global: bool = True,
    ) -> NewsStatistics:
        """
        Optimized method to aggregate statistics using JOIN instead of IN.
        
        This method uses JOIN for better performance when filtering by user_id.
        """
        # Build base query with JOIN for user_id filtering
        # Filter by user_id using JOIN (optimized)
        if include_global:
            # Include user's companies and global companies
            user_filter = or_(
                Company.user_id == user_id,
                Company.user_id.is_(None)  # Global companies
            )
        else:
            # Only user's companies
            user_filter = Company.user_id == user_id
        
        # Total count
        total_result = await self._session.execute(
            select(func.count(NewsItem.id))
            .join(Company, NewsItem.company_id == Company.id)
            .where(user_filter)
        )
        total_count = total_result.scalar() or 0
        
        # Category counts
        category_rows = await self._session.execute(
            select(NewsItem.category, func.count(NewsItem.id))
            .join(Company, NewsItem.company_id == Company.id)
            .where(user_filter)
            .group_by(NewsItem.category)
        )
        category_counts = {
            str(row[0]): row[1]
            for row in category_rows
            if row[0]
        }
        
        # Source type counts
        source_rows = await self._session.execute(
            select(NewsItem.source_type, func.count(NewsItem.id))
            .join(Company, NewsItem.company_id == Company.id)
            .where(user_filter)
            .group_by(NewsItem.source_type)
        )
        source_type_counts = {
            str(row[0]): row[1]
            for row in source_rows
            if row[0]
        }
        
        # Recent count (last 24 hours)
        recent_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).replace(tzinfo=None)
        recent_result = await self._session.execute(
            select(func.count(NewsItem.id))
            .join(Company, NewsItem.company_id == Company.id)
            .where(
                user_filter,
                NewsItem.published_at >= recent_cutoff,
            )
        )
        recent_count = recent_result.scalar() or 0
        
        # High priority count
        high_priority_result = await self._session.execute(
            select(func.count(NewsItem.id))
            .join(Company, NewsItem.company_id == Company.id)
            .where(
                user_filter,
                NewsItem.priority_score >= 0.8,
            )
        )
        high_priority_count = high_priority_result.scalar() or 0
        
        return NewsStatistics(
            total_count=total_count,
            category_counts=category_counts,
            source_type_counts=source_type_counts,
            recent_count=recent_count,
            high_priority_count=high_priority_count,
        )



