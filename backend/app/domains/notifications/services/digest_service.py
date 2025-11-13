"""Domain service for generating personalized digests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import pytz
from loguru import logger
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.repositories import UserPreferencesRepository
from app.models import Company, NewsItem, UserPreferences
from app.models.preferences import DigestFormat


class DigestService:
    """Generates personalized news digests for users."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._preferences = UserPreferencesRepository(session)

    async def generate_user_digest(
        self,
        user_id: str,
        period: str = "daily",
        format_type: str = "short",
        custom_date_from: Optional[datetime] = None,
        custom_date_to: Optional[datetime] = None,
        tracked_only: bool = False,
    ) -> Dict[str, Any]:
        logger.info("Generating %s digest for user %s", period, user_id)
        user_uuid = UUID(user_id)

        user_prefs = await self._preferences.get(user_uuid)
        if user_prefs:
            logger.debug(
                "User preferences: telegram_digest_mode=%s subscribed=%s",
                user_prefs.telegram_digest_mode,
                user_prefs.subscribed_companies,
            )

        if not user_prefs:
            logger.info("Creating default preferences for user %s", user_id)
            user_prefs = await self._preferences.create_default(user_uuid)

        date_from, date_to = self._get_date_range(
            period=period,
            custom_from=custom_date_from,
            custom_to=custom_date_to,
            user_prefs=user_prefs,
        )

        news_items = await self._fetch_news(
            user_prefs=user_prefs,
            date_from=date_from,
            date_to=date_to,
            tracked_only=tracked_only,
        )
        filtered_news = self._filter_news_by_preferences(
            user_prefs=user_prefs,
            news_items=news_items,
            tracked_only=tracked_only,
        )
        ranked_news = self._rank_news_by_relevance(
            news_items=filtered_news,
            user_prefs=user_prefs,
        )

        digest = await self._format_digest_content(
            news_items=ranked_news,
            format_type=format_type,
            date_from=date_from,
            date_to=date_to,
            user_prefs=user_prefs,
            tracked_only=tracked_only,
        )

        logger.info("Digest generated with %s items", len(ranked_news))
        return digest

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_date_range(
        self,
        period: str,
        custom_from: Optional[datetime] = None,
        custom_to: Optional[datetime] = None,
        user_prefs: Optional[UserPreferences] = None,
    ) -> tuple[datetime, datetime]:
        user_tz_name = getattr(user_prefs, "timezone", "UTC") or "UTC"
        try:
            user_tz = pytz.timezone(user_tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning("Unknown timezone: %s, using UTC", user_tz_name)
            user_tz = pytz.UTC

        now_utc = datetime.now(timezone.utc)
        now_user = now_utc.astimezone(user_tz)

        if period == "daily":
            date_from_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)
            date_to_user = now_user.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == "weekly":
            days_since_week_start = (now_user.weekday() + 1) % 7
            week_start = now_user - timedelta(days=days_since_week_start)
            week_end = now_user + timedelta(days=6 - days_since_week_start)
            date_from_user = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            date_to_user = week_end.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == "custom" and custom_from and custom_to:
            date_from_user = self._localize_datetime(custom_from, user_tz, start=True)
            date_to_user = self._localize_datetime(custom_to, user_tz, start=False)
        elif period == "custom":
            date_from_user = (now_user - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            date_to_user = now_user.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            date_from_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)
            date_to_user = now_user.replace(hour=23, minute=59, second=59, microsecond=999999)

        date_from = date_from_user.astimezone(pytz.UTC).replace(tzinfo=None)
        date_to = date_to_user.astimezone(pytz.UTC).replace(tzinfo=None)

        logger.info(
            "Date range for %s digest (timezone: %s): %s to %s UTC",
            period,
            user_tz_name,
            date_from,
            date_to,
        )
        return date_from, date_to

    async def _fetch_news(
        self,
        user_prefs: UserPreferences,
        date_from: datetime,
        date_to: datetime,
        tracked_only: bool,
    ) -> List[NewsItem]:
        logger.info(
            "Fetching news tracked_only=%s subscribed=%s",
            tracked_only,
            user_prefs.subscribed_companies,
        )

        query = select(NewsItem).where(
            and_(
                NewsItem.published_at >= date_from,
                NewsItem.published_at <= date_to,
            )
        )

        if tracked_only and user_prefs.subscribed_companies:
            query = query.where(NewsItem.company_id.in_(user_prefs.subscribed_companies))

        if tracked_only and user_prefs.interested_categories:
            query = query.where(NewsItem.category.in_(user_prefs.interested_categories))

        query = query.order_by(desc(NewsItem.published_at))
        result = await self._session.execute(query)
        news_items = list(result.scalars().all())
        logger.info("Fetched %s news items", len(news_items))
        return news_items

    def _filter_news_by_preferences(
        self,
        user_prefs: UserPreferences,
        news_items: List[NewsItem],
        tracked_only: bool,
    ) -> List[NewsItem]:
        if not user_prefs.keywords:
            return news_items

        filtered: List[NewsItem] = []
        for news in news_items:
            has_keyword = any(
                keyword.lower() in (news.title or "").lower()
                or keyword.lower() in (news.content or "").lower()
                for keyword in user_prefs.keywords
            )
            if not has_keyword and tracked_only and user_prefs.subscribed_companies:
                if news.company_id not in user_prefs.subscribed_companies:
                    continue
            filtered.append(news)
        return filtered

    def _rank_news_by_relevance(
        self,
        news_items: List[NewsItem],
        user_prefs: UserPreferences,
    ) -> List[NewsItem]:
        def calculate_score(news: NewsItem) -> float:
            score = news.priority_score or 0.5
            if user_prefs.subscribed_companies and news.company_id in user_prefs.subscribed_companies:
                score += 0.3
            if user_prefs.interested_categories and news.category in user_prefs.interested_categories:
                score += 0.2
            if user_prefs.keywords:
                keyword_matches = sum(
                    1
                    for keyword in user_prefs.keywords
                    if keyword.lower() in (news.title or "").lower()
                    or keyword.lower() in (news.content or "").lower()
                )
                score += keyword_matches * 0.1

            now = datetime.now(timezone.utc)
            published = news.published_at
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            age_hours = (now - published).total_seconds() / 3600
            if age_hours < 24:
                score += 0.1

            return min(score, 1.0)

        scored_news = [(news, calculate_score(news)) for news in news_items]
        scored_news.sort(key=lambda item: item[1], reverse=True)
        return [news for news, _ in scored_news]

    async def _format_digest_content(
        self,
        news_items: List[NewsItem],
        format_type: str,
        date_from: datetime,
        date_to: datetime,
        user_prefs: UserPreferences,
        tracked_only: bool,
    ) -> Dict[str, Any]:
        return await self._format_digest_by_companies(
            news_items=news_items,
            format_type=format_type,
            date_from=date_from,
            date_to=date_to,
            user_prefs=user_prefs,
        )

    async def _format_digest_by_companies(
        self,
        news_items: List[NewsItem],
        format_type: str,
        date_from: datetime,
        date_to: datetime,
        user_prefs: UserPreferences,
    ) -> Dict[str, Any]:
        by_company: Dict[str, Dict[str, Any]] = {}

        for item in news_items:
            if not item.company_id:
                continue

            company_id_str = str(item.company_id)
            if company_id_str not in by_company:
                company = await self._get_company(item.company_id)
                by_company[company_id_str] = {
                    "company": {
                        "id": str(item.company_id),
                        "name": company.name if company else "Unknown Company",
                        "logo_url": company.logo_url if company else None,
                    },
                    "news": [],
                    "stats": {"total": 0, "by_category": {}},
                }

            formatted_item = await self._format_news_item(item, format_type, user_prefs)
            company_bucket = by_company[company_id_str]
            company_bucket["news"].append(formatted_item)
            company_bucket["stats"]["total"] += 1
            category = item.category or "other"
            company_bucket["stats"]["by_category"][category] = (
                company_bucket["stats"]["by_category"].get(category, 0) + 1
            )

        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "news_count": len(news_items),
            "companies": by_company,
            "companies_count": len(by_company),
            "format": "by_company",
        }

    async def _format_news_item(
        self,
        news_item: NewsItem,
        format_type: str,
        user_prefs: UserPreferences,
    ) -> Dict[str, Any]:
        digest_format = format_type or user_prefs.digest_format or DigestFormat.SHORT.value

        source_value = getattr(news_item, "source", None)
        if not source_value:
            source_type = getattr(news_item, "source_type", None)
            if source_type:
                source_value = getattr(source_type, "value", str(source_type))

        impact_value = getattr(news_item, "impact_score", None)

        base_data = {
            "id": str(news_item.id),
            "title": news_item.title,
            "summary": news_item.summary,
            "category": news_item.category,
            "published_at": news_item.published_at.isoformat() if news_item.published_at else None,
            "source": source_value,
            "source_url": news_item.source_url,
            "priority_score": news_item.priority_score,
            "impact_score": impact_value,
            "company_id": str(news_item.company_id) if news_item.company_id else None,
        }

        if digest_format == DigestFormat.DETAILED.value:
            base_data.update(
                {
                    "content": news_item.content,
                    "tags": news_item.tags,
                    "entities": news_item.entities,
                }
            )

        return base_data

    async def _get_company(self, company_id: UUID) -> Optional[Company]:
        result = await self._session.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _localize_datetime(dt: datetime, timezone_obj: pytz.BaseTzInfo, *, start: bool) -> datetime:
        if dt.tzinfo is None:
            dt = timezone_obj.localize(
                dt.replace(
                    hour=0 if start else 23,
                    minute=0 if start else 59,
                    second=0 if start else 59,
                    microsecond=0 if start else 999999,
                )
            )
        else:
            dt = dt.astimezone(timezone_obj).replace(
                hour=0 if start else 23,
                minute=0 if start else 59,
                second=0 if start else 59,
                microsecond=0 if start else 999999,
            )
        return dt

