"""
Digest generation service
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from loguru import logger
import pytz

from app.models import NewsItem, UserPreferences, Company, NewsCategory
from app.models.preferences import DigestFormat


class DigestService:
    """Service for generating personalized news digests"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_user_digest(
        self,
        user_id: str,
        period: str = "daily",
        format_type: str = "short",
        custom_date_from: Optional[datetime] = None,
        custom_date_to: Optional[datetime] = None,
        tracked_only: bool = False
    ) -> Dict[str, Any]:
        """
        Generate personalized digest for a user
        
        Args:
            user_id: User ID
            period: daily, weekly, or custom
            format_type: short or detailed
            custom_date_from: Start date for custom period
            custom_date_to: End date for custom period
            tracked_only: If True, only include news from tracked companies
            
        Returns:
            Dictionary with digest data
        """
        logger.info(f"Generating {period} digest for user {user_id}, tracked_only={tracked_only}")
        
        # Get user preferences
        result = await self.db.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        user_prefs = result.scalar_one_or_none()
        
        if user_prefs:
            logger.info(f"User preferences: telegram_digest_mode={user_prefs.telegram_digest_mode}, subscribed_companies={user_prefs.subscribed_companies}")
        
        # Create default preferences if they don't exist
        if not user_prefs:
            logger.info(f"Creating default preferences for user {user_id}")
            from app.models.preferences import DigestFrequency, DigestFormat, NotificationFrequency
            import uuid
            
            user_prefs = UserPreferences(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                subscribed_companies=[],
                interested_categories=[],
                keywords=[],
                notification_frequency='daily',
                digest_enabled=True,
                digest_frequency='daily',
                digest_custom_schedule={},
                digest_format='short',
                digest_include_summaries=True,
                telegram_chat_id=None,
                telegram_enabled=False,
                timezone='UTC',
                week_start_day=0
            )
            self.db.add(user_prefs)
            await self.db.commit()
            await self.db.refresh(user_prefs)
        
        # Determine date range with user's timezone
        date_from, date_to = self._get_date_range(
            period, 
            custom_date_from, 
            custom_date_to,
            user_prefs
        )
        
        # Get news items
        news_items = await self._fetch_news(user_prefs, date_from, date_to, tracked_only)
        
        # Filter by preferences (pass tracked_only to control company filtering)
        filtered_news = self._filter_news_by_preferences(user_prefs, news_items, tracked_only)
        
        # Rank by relevance
        ranked_news = self._rank_news_by_relevance(filtered_news, user_prefs)
        
        # Format digest
        digest = await self._format_digest_content(
            ranked_news,
            format_type,
            date_from,
            date_to,
            user_prefs,
            tracked_only
        )
        
        logger.info(f"Digest generated: {len(ranked_news)} news items")
        return digest
    
    def _get_date_range(
        self,
        period: str,
        custom_from: Optional[datetime] = None,
        custom_to: Optional[datetime] = None,
        user_prefs: Optional[UserPreferences] = None
    ) -> tuple[datetime, datetime]:
        """
        Get date range for digest with timezone support
        
        Daily: Current day from 00:00 to 23:59:59 in user's timezone
        Weekly: Current week (configurable start day) in user's timezone
        Custom: User-specified date range
        """
        # Get user's timezone (default to UTC)
        user_tz_name = getattr(user_prefs, 'timezone', 'UTC') if user_prefs else 'UTC'
        if not user_tz_name:
            user_tz_name = 'UTC'
        
        try:
            user_tz = pytz.timezone(user_tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone: {user_tz_name}, falling back to UTC")
            user_tz = pytz.UTC
        
        # Get current time in user's timezone
        now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
        now_user = now_utc.astimezone(user_tz)
        
        logger.debug(f"Period: {period}, User TZ: {user_tz_name}, Now UTC: {now_utc}, Now User: {now_user}")
        
        if period == "daily":
            # Current day: from 00:00:00 to 23:59:59 in user's timezone
            # Get the start of current day (00:00:00)
            date_from_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)
            # Get the end of current day (23:59:59.999999)
            date_to_user = now_user.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            logger.debug(f"Daily digest user TZ range: {date_from_user} to {date_to_user}")
            logger.debug(f"Current user time: {now_user}")
            
            # Convert back to UTC for database query
            date_from = date_from_user.astimezone(pytz.UTC).replace(tzinfo=None)
            date_to = date_to_user.astimezone(pytz.UTC).replace(tzinfo=None)
            
            logger.debug(f"Daily digest UTC range: {date_from} to {date_to}")
            
        elif period == "weekly":
            # Always use Sunday as week start (Western calendar)
            # weekday() returns: Monday=0, Sunday=6
            # We want: Sunday=0, so we calculate days_since_sunday
            days_since_week_start = (now_user.weekday() + 1) % 7
            
            # Start of week (Sunday 00:00:00)
            week_start = now_user - timedelta(days=days_since_week_start)
            date_from_user = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # End of week (Saturday 23:59:59)
            days_until_week_end = 6 - days_since_week_start
            week_end = now_user + timedelta(days=days_until_week_end)
            date_to_user = week_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            logger.debug(f"Weekly digest user TZ range: {date_from_user} to {date_to_user}")
            
            # Convert back to UTC for database query
            date_from = date_from_user.astimezone(pytz.UTC).replace(tzinfo=None)
            date_to = date_to_user.astimezone(pytz.UTC).replace(tzinfo=None)
            
            logger.debug(f"Weekly digest UTC range: {date_from} to {date_to}")
            
        elif period == "custom":
            if custom_from and custom_to:
                # Assume custom dates are in user's timezone
                if custom_from.tzinfo is None:
                    date_from_user = user_tz.localize(custom_from.replace(hour=0, minute=0, second=0, microsecond=0))
                else:
                    date_from_user = custom_from.astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
                
                if custom_to.tzinfo is None:
                    date_to_user = user_tz.localize(custom_to.replace(hour=23, minute=59, second=59, microsecond=999999))
                else:
                    date_to_user = custom_to.astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)
                
                # Convert to UTC
                date_from = date_from_user.astimezone(pytz.UTC).replace(tzinfo=None)
                date_to = date_to_user.astimezone(pytz.UTC).replace(tzinfo=None)
            else:
                # Default to last 7 days
                date_from_user = (now_user - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
                date_to_user = now_user.replace(hour=23, minute=59, second=59, microsecond=999999)
                date_from = date_from_user.astimezone(pytz.UTC).replace(tzinfo=None)
                date_to = date_to_user.astimezone(pytz.UTC).replace(tzinfo=None)
        else:
            # Default to daily
            date_from_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)
            date_to_user = now_user.replace(hour=23, minute=59, second=59, microsecond=999999)
            date_from = date_from_user.astimezone(pytz.UTC).replace(tzinfo=None)
            date_to = date_to_user.astimezone(pytz.UTC).replace(tzinfo=None)
        
        logger.info(f"Date range for {period} digest (timezone: {user_tz_name}): {date_from} to {date_to} UTC")
        logger.info(f"Period details: {period}, User timezone: {user_tz_name}, Current user time: {now_user}")
        return date_from, date_to
    
    async def _fetch_news(
        self,
        user_prefs: UserPreferences,
        date_from: datetime,
        date_to: datetime,
        tracked_only: bool = False
    ) -> List[NewsItem]:
        """Fetch news items based on user preferences and date range"""
        
        logger.info(f"Fetching news: tracked_only={tracked_only}, subscribed_companies={user_prefs.subscribed_companies}")
        logger.info(f"Interested categories: {user_prefs.interested_categories}")
        
        # Build query
        query = select(NewsItem).where(
            and_(
                NewsItem.published_at >= date_from,
                NewsItem.published_at <= date_to
            )
        )
        
        # Filter by subscribed companies if tracked_only is True AND user has subscribed companies
        if tracked_only and user_prefs.subscribed_companies and len(user_prefs.subscribed_companies) > 0:
            logger.info(f"Filtering by tracked companies: {user_prefs.subscribed_companies}")
            query = query.where(NewsItem.company_id.in_(user_prefs.subscribed_companies))
        elif not tracked_only:
            # For "All News" mode, don't filter by companies
            logger.info("All News mode - no company filtering")
            pass
        
        # Filter by interested categories ONLY in tracked_only mode
        # In "All News" mode, show all news (categories are used for ranking/boosting)
        # In "Tracked Only" mode, filter by both companies AND categories
        if tracked_only and user_prefs.interested_categories:
            logger.info(f"Tracked Only mode - filtering by interested categories: {user_prefs.interested_categories}")
            query = query.where(NewsItem.category.in_(user_prefs.interested_categories))
        elif not tracked_only:
            logger.info("All News mode - no category filtering")
        
        # Order by published date (newest first)
        query = query.order_by(desc(NewsItem.published_at))
        
        result = await self.db.execute(query)
        news_items = list(result.scalars().all())
        logger.info(f"Fetched {len(news_items)} news items")
        return news_items
    
    def _filter_news_by_preferences(
        self,
        user_prefs: UserPreferences,
        news_items: List[NewsItem],
        tracked_only: bool = False
    ) -> List[NewsItem]:
        """Filter news items by user preferences"""
        filtered = []
        
        logger.info(f"Filtering {len(news_items)} news items, tracked_only={tracked_only}, keywords={user_prefs.keywords}")
        
        for news in news_items:
            # Check keywords if any
            if user_prefs.keywords:
                has_keyword = any(
                    keyword.lower() in (news.title or "").lower() or
                    keyword.lower() in (news.content or "").lower()
                    for keyword in user_prefs.keywords
                )
                # Only filter by company if tracked_only mode is enabled
                # In "All News" mode, show all news regardless of keywords
                if not has_keyword and tracked_only and user_prefs.subscribed_companies:
                    # Skip if no keyword match and user has specific keyword preferences in tracked_only mode
                    if news.company_id not in user_prefs.subscribed_companies:
                        continue
            
            filtered.append(news)
        
        logger.info(f"After filtering: {len(filtered)} news items")
        return filtered
    
    def _rank_news_by_relevance(
        self,
        news_items: List[NewsItem],
        user_prefs: UserPreferences
    ) -> List[NewsItem]:
        """Rank news items by relevance to user"""
        
        def calculate_score(news: NewsItem) -> float:
            score = news.priority_score or 0.5
            
            # Boost if from subscribed company
            if user_prefs.subscribed_companies and news.company_id in user_prefs.subscribed_companies:
                score += 0.3
            
            # Boost if in interested categories
            if user_prefs.interested_categories and news.category in user_prefs.interested_categories:
                score += 0.2
            
            # Boost if contains keywords
            if user_prefs.keywords:
                keyword_count = sum(
                    1 for keyword in user_prefs.keywords
                    if keyword.lower() in (news.title or "").lower() or
                    keyword.lower() in (news.content or "").lower()
                )
                score += keyword_count * 0.1
            
            # Recent news gets slight boost
            from datetime import timezone
            now = datetime.now(timezone.utc)
            published = news.published_at if news.published_at.tzinfo else news.published_at.replace(tzinfo=timezone.utc)
            age_hours = (now - published).total_seconds() / 3600
            if age_hours < 24:
                score += 0.1
            
            return min(score, 1.0)  # Cap at 1.0
        
        # Calculate scores and sort
        scored_news = [(news, calculate_score(news)) for news in news_items]
        scored_news.sort(key=lambda x: x[1], reverse=True)
        
        return [news for news, score in scored_news]
    
    async def _format_digest_content(
        self,
        news_items: List[NewsItem],
        format_type: str,
        date_from: datetime,
        date_to: datetime,
        user_prefs: UserPreferences,
        tracked_only: bool = False
    ) -> Dict[str, Any]:
        """Format digest content"""
        
        # Always group by companies for better organization
        return await self._format_digest_by_companies(news_items, format_type, date_from, date_to, user_prefs)
    
    async def _format_digest_by_companies(
        self,
        news_items: List[NewsItem],
        format_type: str,
        date_from: datetime,
        date_to: datetime,
        user_prefs: UserPreferences
    ) -> Dict[str, Any]:
        """Format digest content grouped by companies"""
        
        # Group news by companies
        by_company = {}
        for item in news_items:
            if item.company_id:
                company_id = str(item.company_id)
                if company_id not in by_company:
                    # Get company info
                    company_result = await self.db.execute(
                        select(Company).where(Company.id == item.company_id)
                    )
                    company = company_result.scalar_one_or_none()
                    
                    by_company[company_id] = {
                        "company": {
                            "id": str(company.id) if company else str(item.company_id),
                            "name": company.name if company else "Unknown Company",
                            "logo_url": company.logo_url if company else None
                        },
                        "news": [],
                        "stats": {"total": 0, "by_category": {}}
                    }
                
                # Add news item
                formatted_item = await self._format_news_item(item, format_type, user_prefs)
                by_company[company_id]["news"].append(formatted_item)
                by_company[company_id]["stats"]["total"] += 1
                
                # Update category stats
                cat = item.category or "other"
                by_company[company_id]["stats"]["by_category"][cat] = \
                    by_company[company_id]["stats"]["by_category"].get(cat, 0) + 1
        
        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "news_count": len(news_items),
            "companies": by_company,
            "companies_count": len(by_company),
            "format": "by_company"
        }
    
    async def _format_news_item(
        self,
        news: NewsItem,
        format_type: str,
        user_prefs: UserPreferences
    ) -> Dict[str, Any]:
        """Format a single news item"""
        
        # Get company info
        company = None
        if news.company_id:
            result = await self.db.execute(
                select(Company).where(Company.id == news.company_id)
            )
            company = result.scalar_one_or_none()
        
        item = {
            "id": str(news.id),
            "title": news.title,
            "source_url": news.source_url,
            "published_at": news.published_at.isoformat(),
            "category": news.category,
            "priority_score": news.priority_score,
            "company": {
                "id": str(company.id),
                "name": company.name,
                "logo_url": company.logo_url
            } if company else None
        }
        
        # Add summary if format is detailed or user prefers summaries
        if format_type == "detailed" or user_prefs.digest_include_summaries:
            item["summary"] = news.summary
        
        # Add full content only for detailed format
        if format_type == "detailed":
            item["content"] = news.content
        
        return item
    
    def _get_digest_statistics(self, news_items: List[NewsItem]) -> Dict[str, Any]:
        """Get digest statistics"""
        
        total = len(news_items)
        if total == 0:
            return {
                "total_news": 0,
                "by_category": {},
                "by_source": {},
                "avg_priority": 0
            }
        
        # Category distribution
        by_category = {}
        for news in news_items:
            category = news.category or "uncategorized"
            by_category[category] = by_category.get(category, 0) + 1
        
        # Source type distribution
        by_source = {}
        for news in news_items:
            source = news.source_type or "unknown"
            by_source[source] = by_source.get(source, 0) + 1
        
        # Average priority
        avg_priority = sum(news.priority_score or 0.5 for news in news_items) / total
        
        return {
            "total_news": total,
            "by_category": by_category,
            "by_source": by_source,
            "avg_priority": round(avg_priority, 2)
        }
    
    def _empty_digest(self, period: str) -> Dict[str, Any]:
        """Return empty digest structure"""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        return {
            "date_from": now.isoformat(),
            "date_to": now.isoformat(),
            "news_count": 0,
            "categories": {},
            "statistics": {
                "total_news": 0,
                "by_category": {},
                "by_source": {},
                "avg_priority": 0
            },
            "format": "short"
        }
    
    def format_digest_for_telegram(self, digest_data: Dict[str, Any], user_prefs: UserPreferences = None) -> str:
        """Format digest for Telegram message with company grouping"""
        
        if digest_data["news_count"] == 0:
            return "📭 No news for the selected period"
        
        lines = []
        lines.append(f"📰 **News Digest**")
        lines.append(f"📅 {digest_data['date_from'][:10]} - {digest_data['date_to'][:10]}")
        lines.append(f"📊 Total news: {digest_data['news_count']}")
        
        if digest_data.get('companies_count'):
            lines.append(f"🏢 Companies: {digest_data['companies_count']}")
        
        lines.append("")  # Empty line
        
        # Format by companies (new format)
        if digest_data.get('companies'):
            for company_id, company_data in digest_data['companies'].items():
                company = company_data['company']
                stats = company_data['stats']
                
                lines.append(f"🏢 **{company['name']}** ({stats['total']} news)")
                
                # Group by categories within company
                for category, count in stats['by_category'].items():
                    category_emoji = self._get_category_emoji(category)
                    lines.append(f"└─ {category_emoji} {self._format_category_name(category)} ({count})")
                    
                    # Show all news items for this category
                    category_news = [news for news in company_data['news'] 
                                   if (news.get('category') or 'other') == category]
                    
                    for news in category_news:
                        title = news['title']
                        if len(title) > 60:
                            title = title[:57] + "..."
                        lines.append(f"   • {title}")
                        lines.append(f"     🔗 {news['source_url']}")
                
                lines.append("")  # Empty line between companies
        
        # Fallback to old format (by categories) if companies not available
        elif digest_data.get('categories'):
            for category, news_items in digest_data["categories"].items():
                if not news_items:
                    continue
                
                category_emoji = self._get_category_emoji(category)
                lines.append(f"\n{category_emoji} **{self._format_category_name(category)}** ({len(news_items)})")
                
                for i, news in enumerate(news_items, 1):  # Show all news items
                    company_name = news.get("company", {}).get("name", "Unknown") if news.get("company") else "Unknown"
                    # Truncate long titles to save space
                    title = news['title']
                    if len(title) > 80:
                        title = title[:77] + "..."
                    
                    # Add bold font for title and indentation
                    lines.append(f"\n{i}. **{title}**")
                    lines.append(f"   🏢 {company_name}")
                    lines.append(f"   🔗 {news['source_url']}")
        
        return "\n".join(lines)
    
    def _get_category_emoji(self, category: str) -> str:
        """Get emoji for category"""
        emoji_map = {
            "product_update": "🚀",
            "pricing_change": "💰",
            "strategic_announcement": "📢",
            "technical_update": "⚙️",
            "funding_news": "💵",
            "research_paper": "📄",
            "community_event": "🎉",
            "partnership": "🤝",
            "acquisition": "🏢",
            "integration": "🔗",
            "security_update": "🔒",
            "api_update": "🔌",
            "model_release": "🤖",
            "performance_improvement": "⚡",
            "feature_deprecation": "⚠️"
        }
        return emoji_map.get(category, "📌")
    
    def _format_category_name(self, category: str) -> str:
        """Format category name for display"""
        return category.replace("_", " ").title()

