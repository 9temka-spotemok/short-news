"""
Competitor analysis service
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_, func, desc

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import uuid
import math

from app.models import NewsItem, Company, CompetitorComparison, NewsTopic, SentimentLabel, SourceType
from app.domains.competitors.repositories import CompetitorRepository


class CompetitorAnalysisService:
    """Service for competitor analysis and comparison"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._competitor_repo = CompetitorRepository(db)
    
    async def compare_companies(
        self,
        company_ids: List[str],
        date_from: datetime,
        date_to: datetime,
        user_id: Optional[str] = None,  # Пока не используется
        comparison_name: Optional[str] = None,  # Пока не используется
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple companies
        
        Args:
            company_ids: List of company IDs to compare
            date_from: Start date
            date_to: End date
            user_id: User ID (currently not used - will be used for saving reports)
            comparison_name: Optional name for the comparison (currently not used)
            
        Returns:
            Comparison data with metrics and company information
        """
        logger.info(f"Comparing {len(company_ids)} companies from {date_from} to {date_to}")
        
        # Get company info
        companies = await self._get_companies(company_ids)
        
        # Calculate metrics for each company
        metrics = {
            "news_volume": {},
            "category_distribution": {},
            "topic_distribution": {},
            "sentiment_distribution": {},
            "activity_score": {},
            "avg_priority": {},
            "daily_activity": {},
            "top_news": {}
        }
        
        for company_id in company_ids:
            company_uuid = uuid.UUID(company_id)
            company_metrics = await self.build_company_metrics(
                company_uuid,
                date_from,
                date_to,
                filters=filters,
                top_news_limit=5,
            )

            metrics["news_volume"][company_id] = company_metrics["news_volume"]
            metrics["category_distribution"][company_id] = company_metrics["category_distribution"]
            metrics["topic_distribution"][company_id] = company_metrics["topic_distribution"]
            metrics["sentiment_distribution"][company_id] = company_metrics["sentiment_distribution"]
            metrics["activity_score"][company_id] = company_metrics["activity_score"]
            metrics["avg_priority"][company_id] = company_metrics["avg_priority"]
            metrics["daily_activity"][company_id] = company_metrics["daily_activity"]
            metrics["top_news"][company_id] = company_metrics["top_news"]
        
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
            "metrics": metrics,
        }

        if filters:
            comparison_data["filters"] = {
                "topics": [topic.value for topic in filters.get("topics", [])],
                "sentiments": [sent.value for sent in filters.get("sentiments", [])],
                "source_types": [stype.value for stype in filters.get("source_types", [])],
                "min_priority": filters.get("min_priority"),
            }

        # TODO: Временно убираем сохранение в БД для исправления ошибки 500
        # Позже добавим полную функциональность сохранения отчетов
        # if user_id:
        #     await self._save_comparison(
        #         user_id, company_ids, date_from, date_to, comparison_name, metrics
        #     )
        
        return comparison_data
    
    def _build_conditions(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        conditions = [
            NewsItem.company_id == company_id,
            NewsItem.published_at >= date_from,
            NewsItem.published_at <= date_to,
        ]

        if filters:
            topics = filters.get("topics") or []
            sentiments = filters.get("sentiments") or []
            source_types = filters.get("source_types") or []
            min_priority = filters.get("min_priority")

            if topics:
                conditions.append(NewsItem.topic.in_(topics))
            if sentiments:
                conditions.append(NewsItem.sentiment.in_(sentiments))
            if source_types:
                conditions.append(NewsItem.source_type.in_(source_types))
            if min_priority is not None:
                conditions.append(NewsItem.priority_score >= float(min_priority))

        return conditions

    async def get_news_volume(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Get total news volume for a company"""
        conditions = self._build_conditions(company_id, date_from, date_to, filters)
        result = await self.db.execute(
            select(func.count(NewsItem.id))
            .where(and_(*conditions))
        )
        return result.scalar() or 0
    
    async def get_category_distribution(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        """Get category distribution for a company"""
        conditions = self._build_conditions(company_id, date_from, date_to, filters)
        result = await self.db.execute(
            select(NewsItem.category, func.count(NewsItem.id).label('count'))
            .where(and_(*conditions))
            .group_by(NewsItem.category)
        )
        
        distribution = {}
        for category, count in result.all():
            if category:
                distribution[category] = count
        
        return distribution

    async def get_topic_distribution(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        conditions = self._build_conditions(company_id, date_from, date_to, filters)
        result = await self.db.execute(
            select(NewsItem.topic, func.count(NewsItem.id).label('count'))
            .where(and_(*conditions))
            .group_by(NewsItem.topic)
        )

        distribution: Dict[str, int] = {}
        for topic, count in result.all():
            if topic:
                topic_value = topic.value if hasattr(topic, "value") else str(topic)
                distribution[topic_value] = count
        return distribution

    async def get_sentiment_distribution(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        conditions = self._build_conditions(company_id, date_from, date_to, filters)
        result = await self.db.execute(
            select(NewsItem.sentiment, func.count(NewsItem.id).label('count'))
            .where(and_(*conditions))
            .group_by(NewsItem.sentiment)
        )

        distribution: Dict[str, int] = {}
        for sentiment, count in result.all():
            if sentiment:
                sentiment_value = sentiment.value if hasattr(sentiment, "value") else str(sentiment)
                distribution[sentiment_value] = count
        return distribution
    
    async def get_activity_score(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate activity score for a company
        
        Score is based on:
        - News volume (weighted)
        - Category diversity
        - Recency of news
        """
        # Get news items
        conditions = self._build_conditions(company_id, date_from, date_to, filters)
        result = await self.db.execute(
            select(NewsItem)
            .where(and_(*conditions))
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
        from datetime import timezone as tz
        now = datetime.now(tz.utc)
        days_range = (date_to - date_from).days or 1
        recent_news = sum(1 for item in news_items if item.published_at and (now - (item.published_at if item.published_at.tzinfo else item.published_at.replace(tzinfo=tz.utc))).days <= days_range / 2)
        recency_score = min((recent_news / volume) * 30, 30) if volume > 0 else 0
        
        total_score = volume_score + diversity_score + recency_score
        
        return round(total_score, 2)

    async def get_average_priority(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> float:
        conditions = self._build_conditions(company_id, date_from, date_to, filters)
        result = await self.db.execute(
            select(func.avg(NewsItem.priority_score)).where(and_(*conditions))
        )
        avg_priority = result.scalar()
        return float(avg_priority) if avg_priority is not None else 0.0
    
    async def get_daily_activity(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        """Get daily activity breakdown"""
        conditions = self._build_conditions(company_id, date_from, date_to, filters)
        result = await self.db.execute(
            select(
                func.date(NewsItem.published_at).label('date'),
                func.count(NewsItem.id).label('count')
            )
            .where(and_(*conditions))
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
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get top news items for a company"""
        conditions = self._build_conditions(company_id, date_from, date_to, filters)
        result = await self.db.execute(
            select(NewsItem)
            .where(and_(*conditions))
            .order_by(desc(NewsItem.priority_score), desc(NewsItem.published_at))
            .limit(limit)
        )
        
        news_items = result.scalars().all()
        
        return [
            {
                "id": str(item.id),
                "title": item.title,
                "category": item.category.value if hasattr(item.category, "value") else item.category,
                "topic": item.topic.value if hasattr(item.topic, "value") else item.topic,
                "sentiment": item.sentiment.value if hasattr(item.sentiment, "value") else item.sentiment,
                "source_type": item.source_type.value if hasattr(item.source_type, "value") else item.source_type,
                "published_at": item.published_at.isoformat(),
                "source_url": item.source_url,
                "priority_score": item.priority_score
            }
            for item in news_items
        ]
    
    async def build_company_metrics(
        self,
        company_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        *,
        filters: Optional[Dict[str, Any]] = None,
        top_news_limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Build the complete metrics bundle for a single company within the requested window.
        The method is shared across comparison endpoints to avoid duplicated aggregation logic.
        """
        news_volume = await self.get_news_volume(company_id, date_from, date_to, filters)
        category_distribution = await self.get_category_distribution(company_id, date_from, date_to, filters)
        topic_distribution = await self.get_topic_distribution(company_id, date_from, date_to, filters)
        sentiment_distribution = await self.get_sentiment_distribution(company_id, date_from, date_to, filters)
        activity_score = await self.get_activity_score(company_id, date_from, date_to, filters)
        avg_priority = await self.get_average_priority(company_id, date_from, date_to, filters)
        daily_activity = await self.get_daily_activity(company_id, date_from, date_to, filters)
        top_news = await self.get_top_news(
            company_id,
            date_from,
            date_to,
            limit=top_news_limit,
            filters=filters,
        )

        return {
            "news_volume": news_volume,
            "category_distribution": category_distribution,
            "topic_distribution": topic_distribution,
            "sentiment_distribution": sentiment_distribution,
            "activity_score": activity_score,
            "avg_priority": avg_priority,
            "daily_activity": daily_activity,
            "top_news": top_news,
        }
    
    def _get_mock_companies(self, company_ids: List[str]) -> List[Company]:
        """Get mock company objects when DB is unavailable"""
        mock_companies = []
        
        # Создаем мок-объекты компаний
        for i, company_id in enumerate(company_ids):
            mock_company = Company()
            mock_company.id = uuid.UUID(company_id)
            mock_company.name = f"Company {i+1}"
            mock_company.logo_url = f"https://example.com/logo{i+1}.png"
            mock_company.category = "llm_provider"
            mock_companies.append(mock_company)
        
        logger.info(f"Created {len(mock_companies)} mock companies")
        return mock_companies
    
    def _get_mock_competitor_suggestions(self, company_id: uuid.UUID, limit: int) -> List[Dict[str, Any]]:
        """Get mock competitor suggestions when DB is unavailable"""
        mock_suggestions = []
        
        for i in range(min(limit, 5)):
            mock_suggestion = {
                "company": {
                    "id": str(uuid.uuid4()),  # Генерируем валидный UUID
                    "name": f"Competitor {i+1}",
                    "website": f"https://competitor{i+1}.com",
                    "description": f"This is a mock competitor {i+1} for testing purposes",
                    "logo_url": f"https://example.com/competitor{i+1}.png",
                    "category": "llm_provider"
                },
                "similarity_score": round(0.8 - (i * 0.1), 2),
                "common_categories": ["product_update", "technical_update"],
                "reason": "Similar activity level and news patterns"
            }
            mock_suggestions.append(mock_suggestion)
        
        logger.info(f"Created {len(mock_suggestions)} mock competitor suggestions")
        return mock_suggestions
    
    async def _get_companies(self, company_ids: List[str]) -> List[Company]:
        """Get company objects"""
        try:
            return await self._competitor_repo.fetch_companies(company_ids)
        except Exception as e:
            logger.error(f"Error getting companies: {e}")
            raise
    
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
            comparison = await self._competitor_repo.save_comparison(
                user_id=user_id,
                company_ids=company_ids,
                date_from=date_from,
                date_to=date_to,
                name=name,
                metrics=metrics,
            )

            logger.info(f"Comparison saved: {comparison.id}")
            return comparison
        except Exception as e:
            logger.error(f"Error saving comparison: {e}")
            await self.db.rollback()
            raise
    
    async def get_user_comparisons(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's saved comparisons"""
        return await self._competitor_repo.list_user_comparisons(user_id, limit)
    
    async def get_comparison(self, comparison_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get specific comparison"""
        comparison = await self._competitor_repo.get_comparison(comparison_id, user_id)
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
            return await self._competitor_repo.delete_comparison(comparison_id, user_id)
        except Exception as e:
            logger.error(f"Error deleting comparison: {e}")
            await self.db.rollback()
            return False

    async def suggest_competitors(
        self,
        company_id: uuid.UUID,
        limit: int = 5,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Подобрать конкурентов для компании
        
        Алгоритм:
        1. Получить профиль компании (категории новостей, источники, активность)
        2. Найти компании с похожими профилями
        3. Ранжировать по схожести
        
        Returns:
            [
                {
                    "company": {...},
                    "similarity_score": 0.85,
                    "common_categories": ["product_update", "technical_update"],
                    "reason": "Similar news patterns and activity level"
                },
                ...
            ]
        """
        logger.info(f"Suggesting competitors for company {company_id}")
        
        try:
            # Set default date range if not provided
            if not date_from:
                date_from = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
            if not date_to:
                date_to = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # 1. Получить профиль целевой компании
            target_profile = await self._get_company_profile(company_id, date_from, date_to)
            
            # 2. Получить профили других компаний (ограничиваем до 50 для производительности)
            all_companies = await self._get_all_companies_except(company_id, limit=50)
            
            if not all_companies:
                logger.warning(f"No other companies found for competitor analysis")
                return []
            
            candidates = []
            
            # Обрабатываем компании с обработкой ошибок
            for company in all_companies:
                try:
                    company_profile = await self._get_company_profile(company.id, date_from, date_to)
                    
                    # 3. Посчитать схожесть
                    similarity = self._calculate_similarity(target_profile, company_profile)
                    
                    if similarity > 0.3:  # Минимальный порог
                        candidates.append({
                            "company": {
                                "id": str(company.id),
                                "name": company.name,
                                "website": company.website,
                                "description": company.description,
                                "logo_url": company.logo_url,
                                "category": company.category
                            },
                            "similarity_score": similarity,
                            "common_categories": self._find_common_categories(target_profile, company_profile),
                            "reason": self._generate_reason(target_profile, company_profile)
                        })
                except Exception as e:
                    logger.warning(f"Error processing company {company.id} for competitor analysis: {e}")
                    continue
            
            # 4. Отсортировать по схожести
            candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
            return candidates[:limit]
            
        except Exception as e:
            logger.error(f"Error suggesting competitors for company {company_id}: {e}", exc_info=True)
            return []
    
    def _calculate_similarity(
        self, 
        profile1: Dict[str, Any], 
        profile2: Dict[str, Any]
    ) -> float:
        """
        Считаем схожесть как взвешенную сумму:
        - Схожесть категорий новостей (40%)
        - Схожесть источников (30%)
        - Схожесть активности (20%)
        - Схожесть категории компании (10%)
        """
        
        # Косинусное сходство для категорий
        category_sim = self._cosine_similarity(
            profile1["category_distribution"],
            profile2["category_distribution"]
        )
        
        # Косинусное сходство для источников
        source_sim = self._cosine_similarity(
            profile1["source_distribution"],
            profile2["source_distribution"]
        )
        
        # Схожесть активности (обратная разница)
        activity_diff = abs(profile1["activity_level"] - profile2["activity_level"])
        max_activity = max(profile1["activity_level"], profile2["activity_level"])
        activity_sim = 1 - (activity_diff / max_activity) if max_activity > 0 else 0
        
        # Категория компании (0 или 1)
        category_match = 1.0 if profile1["company_category"] == profile2["company_category"] else 0.0
        
        # Взвешенная сумма
        total_similarity = (
            category_sim * 0.4 +
            source_sim * 0.3 +
            activity_sim * 0.2 +
            category_match * 0.1
        )
        
        return round(total_similarity, 2)
    
    def _cosine_similarity(self, dict1: Dict[str, int], dict2: Dict[str, int]) -> float:
        """Calculate cosine similarity between two dictionaries"""
        # Get all unique keys
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        if not all_keys:
            return 0.0
        
        # Create vectors
        vec1 = [dict1.get(key, 0) for key in all_keys]
        vec2 = [dict2.get(key, 0) for key in all_keys]
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def _get_company_profile(
        self, 
        company_id: uuid.UUID, 
        date_from: datetime, 
        date_to: datetime
    ) -> Dict[str, Any]:
        """Get comprehensive company profile"""
        
        try:
            # Get company info
            result = await self.db.execute(
                select(Company).where(Company.id == company_id)
            )
            company = result.scalar_one_or_none()
            
            if not company:
                return {
                    "category_distribution": {},
                    "source_distribution": {},
                    "activity_level": 0,
                    "avg_priority": 0.0,
                    "company_category": "unknown"
                }
            
            # Get news items with limit to avoid loading too many
            result = await self.db.execute(
                select(NewsItem)
                .where(
                    and_(
                        NewsItem.company_id == company_id,
                        NewsItem.published_at >= date_from,
                        NewsItem.published_at <= date_to
                    )
                )
                .limit(1000)  # Limit to avoid loading too many news items
            )
            news_items = list(result.scalars().all())
            
            # Calculate distributions
            category_distribution = {}
            source_distribution = {}
            total_priority = 0.0
            
            for item in news_items:
                # Category distribution
                if item.category:
                    cat_key = item.category.value if hasattr(item.category, 'value') else str(item.category)
                    category_distribution[cat_key] = category_distribution.get(cat_key, 0) + 1
                
                # Source distribution
                if item.source_type:
                    source_key = item.source_type.value if hasattr(item.source_type, 'value') else str(item.source_type)
                    source_distribution[source_key] = source_distribution.get(source_key, 0) + 1
                
                # Priority
                total_priority += item.priority_score or 0
            
            avg_priority = total_priority / len(news_items) if news_items else 0.0
            
            return {
                "category_distribution": category_distribution,
                "source_distribution": source_distribution,
                "activity_level": len(news_items),
                "avg_priority": avg_priority,
                "company_category": company.category or "unknown"
            }
        except Exception as e:
            logger.error(f"Error getting company profile for {company_id}: {e}", exc_info=True)
            return {
                "category_distribution": {},
                "source_distribution": {},
                "activity_level": 0,
                "avg_priority": 0.0,
                "company_category": "unknown"
            }
    
    async def _get_all_companies_except(self, exclude_id: uuid.UUID, limit: int = 100) -> List[Company]:
        """Get all companies except the excluded one, with a limit to avoid loading too many"""
        try:
            result = await self.db.execute(
                select(Company)
                .where(Company.id != exclude_id)
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error fetching companies for competitor analysis: {e}", exc_info=True)
            return []
    
    def _find_common_categories(
        self, 
        profile1: Dict[str, Any], 
        profile2: Dict[str, Any]
    ) -> List[str]:
        """Find common categories between two profiles"""
        categories1 = set(profile1["category_distribution"].keys())
        categories2 = set(profile2["category_distribution"].keys())
        common = categories1.intersection(categories2)
        return list(common)
    
    def _generate_reason(
        self, 
        profile1: Dict[str, Any], 
        profile2: Dict[str, Any]
    ) -> str:
        """Generate human-readable reason for similarity"""
        reasons = []
        
        # Check activity similarity
        activity_diff = abs(profile1["activity_level"] - profile2["activity_level"])
        if activity_diff <= 5:
            reasons.append("similar activity level")
        
        # Check category similarity
        common_categories = self._find_common_categories(profile1, profile2)
        if len(common_categories) >= 2:
            reasons.append("similar news patterns")
        
        # Check company category
        if profile1["company_category"] == profile2["company_category"]:
            reasons.append(f"same industry ({profile1['company_category']})")
        
        # Check priority similarity
        priority_diff = abs(profile1["avg_priority"] - profile2["avg_priority"])
        if priority_diff <= 0.2:
            reasons.append("similar news priority")
        
        if not reasons:
            return "general similarity"
        
        return ", ".join(reasons)
    
    async def analyze_news_themes(
        self,
        company_ids: List[uuid.UUID],
        date_from: datetime,
        date_to: datetime
    ) -> Dict[str, Any]:
        """
        Анализ новостных тем для списка компаний
        
        Returns:
            {
                "themes": {
                    "ai": {
                        "total_mentions": 45,
                        "by_company": {
                            "company_id_1": 20,
                            "company_id_2": 15,
                            ...
                        },
                        "example_titles": [...]
                    },
                    "api": {...},
                    ...
                },
                "unique_themes": {
                    "company_id_1": ["custom_theme_1", ...],
                    ...
                }
            }
        """
        logger.info(f"Analyzing themes for {len(company_ids)} companies")
        
        # 1. Получить все новости для всех компаний
        news_by_company = {}
        for company_id in company_ids:
            news = await self._fetch_company_news(company_id, date_from, date_to)
            news_by_company[str(company_id)] = news
        
        # 2. Извлечь ключевые слова из заголовков
        all_keywords = {}
        for company_id, news_list in news_by_company.items():
            for news in news_list:
                keywords = self._extract_keywords(news.title)
                for keyword in keywords:
                    if keyword not in all_keywords:
                        all_keywords[keyword] = {
                            "total_mentions": 0,
                            "by_company": {},
                            "example_titles": []
                        }
                    all_keywords[keyword]["total_mentions"] += 1
                    all_keywords[keyword]["by_company"][company_id] = \
                        all_keywords[keyword]["by_company"].get(company_id, 0) + 1
                    if len(all_keywords[keyword]["example_titles"]) < 3:
                        all_keywords[keyword]["example_titles"].append(news.title)
        
        # 3. Найти уникальные темы для каждой компании
        unique_themes = {}
        for company_id in company_ids:
            company_keywords = [
                kw for kw, data in all_keywords.items()
                if str(company_id) in data["by_company"] 
                and len(data["by_company"]) == 1  # Только у этой компании
            ]
            unique_themes[str(company_id)] = company_keywords
        
        return {
            "themes": all_keywords,
            "unique_themes": unique_themes
        }
    
    def _extract_keywords(self, title: str) -> List[str]:
        """
        Извлечь ключевые слова из заголовка
        
        Простая версия:
        - Убрать стоп-слова
        - Привести к нижнему регистру
        - Оставить слова длиннее 3 символов
        """
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'from', 'up', 'down', 'out', 'off',
            'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there',
            'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few',
            'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
            'own', 'same', 'so', 'than', 'too', 'very', 'can', 'just', 'now'
        }
        
        words = title.lower().split()
        keywords = [
            word.strip('.,!?;:()[]{}"\'') 
            for word in words 
            if len(word) > 3 and word not in stopwords
        ]
        
        return keywords
    
    async def _fetch_company_news(
        self, 
        company_id: uuid.UUID, 
        date_from: datetime, 
        date_to: datetime
    ) -> List[NewsItem]:
        """Fetch news items for a company in date range"""
        result = await self.db.execute(
            select(NewsItem)
            .where(
                and_(
                    NewsItem.company_id == company_id,
                    NewsItem.published_at >= date_from,
                    NewsItem.published_at <= date_to
                )
            )
            .order_by(desc(NewsItem.published_at))
        )
        return list(result.scalars().all())


# Alias for backward compatibility
CompetitorService = CompetitorAnalysisService