"""
Notification service for micro-notifications (Dota 2 style)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from loguru import logger
import uuid

from app.models import (
    Notification, NotificationSettings, NotificationType, NotificationPriority,
    NewsItem, UserPreferences, Company
)


class NotificationService:
    """Service for creating and managing micro-notifications"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM
    ) -> Optional[Notification]:
        """
        Create a new notification for a user
        
        Args:
            user_id: User ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            data: Additional data (JSON)
            priority: Notification priority
            
        Returns:
            Created notification or None
        """
        try:
            # Check if user has notifications enabled
            settings = await self._get_user_settings(user_id)
            if not settings or not settings.enabled:
                return None
            
            # Check if this type is enabled
            if not self._is_type_enabled(settings, notification_type):
                return None
            
            notification = Notification(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                type=notification_type,
                title=title,
                message=message,
                data=data or {},
                priority=priority,
                is_read=False
            )
            
            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification)
            
            logger.info(f"Notification created: {notification_type} for user {user_id}")
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            await self.db.rollback()
            return None
    
    async def check_new_news_triggers(self, news_item: NewsItem) -> List[Notification]:
        """
        Check if a new news item triggers any notifications
        
        Args:
            news_item: Newly created news item
            
        Returns:
            List of created notifications
        """
        notifications = []
        
        # Get all users with notification settings
        result = await self.db.execute(
            select(NotificationSettings).where(NotificationSettings.enabled == True)
        )
        settings_list = result.scalars().all()
        
        for settings in settings_list:
            # Get user preferences
            user_prefs = await self._get_user_preferences(str(settings.user_id))
            if not user_prefs:
                continue
            
            # Check if news matches user interests
            should_notify = False
            notification_type = NotificationType.NEW_NEWS
            priority = NotificationPriority.MEDIUM
            
            # Check subscribed companies
            if settings.company_alerts and user_prefs.subscribed_companies:
                if news_item.company_id in user_prefs.subscribed_companies:
                    should_notify = True
                    
                    # Check for special categories with higher priority
                    if news_item.category == "pricing_change":
                        notification_type = NotificationType.PRICING_CHANGE
                        priority = NotificationPriority.HIGH
                    elif news_item.category == "funding_news":
                        notification_type = NotificationType.FUNDING_ANNOUNCEMENT
                        priority = NotificationPriority.HIGH
                    elif news_item.category == "product_update":
                        notification_type = NotificationType.PRODUCT_LAUNCH
                        priority = NotificationPriority.MEDIUM
            
            # Check keywords
            if settings.keyword_alerts and user_prefs.keywords:
                for keyword in user_prefs.keywords:
                    if (keyword.lower() in (news_item.title or "").lower() or
                        keyword.lower() in (news_item.content or "").lower()):
                        should_notify = True
                        notification_type = NotificationType.KEYWORD_MATCH
                        priority = NotificationPriority.HIGH
                        break
            
            # Check priority score threshold
            if should_notify and settings.min_priority_score:
                if (news_item.priority_score or 0) < settings.min_priority_score:
                    should_notify = False
            
            if should_notify:
                # Get company name
                company_name = "Unknown"
                if news_item.company_id:
                    company = await self._get_company(news_item.company_id)
                    company_name = company.name if company else "Unknown"
                
                notification = await self.create_notification(
                    user_id=str(settings.user_id),
                    notification_type=notification_type,
                    title=f"{company_name}: {news_item.category or 'News'}",
                    message=news_item.title,
                    data={
                        "news_id": str(news_item.id),
                        "company_id": str(news_item.company_id) if news_item.company_id else None,
                        "category": news_item.category,
                        "source_url": news_item.source_url
                    },
                    priority=priority
                )
                
                if notification:
                    notifications.append(notification)
        
        return notifications
    
    async def check_company_activity(self, hours: int = 24) -> List[Notification]:
        """
        Check for high company activity (Dota 2 style: multiple events)
        
        Args:
            hours: Number of hours to check
            
        Returns:
            List of created notifications
        """
        notifications = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get companies with 3+ news in the period
        result = await self.db.execute(
            select(NewsItem.company_id, func.count(NewsItem.id).label('count'))
            .where(NewsItem.published_at >= cutoff_time)
            .group_by(NewsItem.company_id)
            .having(func.count(NewsItem.id) >= 3)
        )
        active_companies = result.all()
        
        for company_id, news_count in active_companies:
            if not company_id:
                continue
            
            # Get users watching this company
            result = await self.db.execute(
                select(UserPreferences)
                .where(UserPreferences.subscribed_companies.contains([company_id]))
            )
            user_prefs_list = result.scalars().all()
            
            for user_prefs in user_prefs_list:
                # Check if user has this notification type enabled
                settings = await self._get_user_settings(str(user_prefs.user_id))
                if not settings or not settings.enabled or not settings.company_alerts:
                    continue
                
                # Get company info
                company = await self._get_company(company_id)
                if not company:
                    continue
                
                notification = await self.create_notification(
                    user_id=str(user_prefs.user_id),
                    notification_type=NotificationType.COMPANY_ACTIVE,
                    title=f"High Activity: {company.name}",
                    message=f"{company.name} has published {news_count} news items in the last {hours} hours",
                    data={
                        "company_id": str(company_id),
                        "news_count": news_count,
                        "hours": hours
                    },
                    priority=NotificationPriority.MEDIUM
                )
                
                if notification:
                    notifications.append(notification)
        
        return notifications
    
    async def check_category_trends(self, hours: int = 24, threshold: int = 5) -> List[Notification]:
        """
        Check for category trends (Dota 2 style: pattern detection)
        
        Args:
            hours: Number of hours to check
            threshold: Minimum news count to trigger trend notification
            
        Returns:
            List of created notifications
        """
        notifications = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get categories with many news
        result = await self.db.execute(
            select(NewsItem.category, func.count(NewsItem.id).label('count'))
            .where(NewsItem.published_at >= cutoff_time)
            .group_by(NewsItem.category)
            .having(func.count(NewsItem.id) >= threshold)
        )
        trending_categories = result.all()
        
        for category, news_count in trending_categories:
            if not category:
                continue
            
            # Get users interested in this category
            result = await self.db.execute(
                select(UserPreferences)
                .where(UserPreferences.interested_categories.contains([category]))
            )
            user_prefs_list = result.scalars().all()
            
            for user_prefs in user_prefs_list:
                # Check if user has trend notifications enabled
                settings = await self._get_user_settings(str(user_prefs.user_id))
                if not settings or not settings.enabled or not settings.category_trends:
                    continue
                
                notification = await self.create_notification(
                    user_id=str(user_prefs.user_id),
                    notification_type=NotificationType.CATEGORY_TREND,
                    title=f"Trending: {category.replace('_', ' ').title()}",
                    message=f"{news_count} news items in {category.replace('_', ' ')} category in the last {hours} hours",
                    data={
                        "category": category,
                        "news_count": news_count,
                        "hours": hours
                    },
                    priority=NotificationPriority.LOW
                )
                
                if notification:
                    notifications.append(notification)
        
        return notifications
    
    async def _get_user_settings(self, user_id: str) -> Optional[NotificationSettings]:
        """Get user notification settings"""
        result = await self.db.execute(
            select(NotificationSettings).where(NotificationSettings.user_id == uuid.UUID(user_id))
        )
        return result.scalar_one_or_none()
    
    async def _get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences"""
        result = await self.db.execute(
            select(UserPreferences).where(UserPreferences.user_id == uuid.UUID(user_id))
        )
        return result.scalar_one_or_none()
    
    async def _get_company(self, company_id: uuid.UUID) -> Optional[Company]:
        """Get company by ID"""
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()
    
    def _is_type_enabled(self, settings: NotificationSettings, notification_type: NotificationType) -> bool:
        """Check if notification type is enabled for user"""
        if not settings.notification_types:
            return True  # Default: all enabled
        
        type_config = settings.notification_types.get(notification_type.value, {})
        if isinstance(type_config, bool):
            return type_config
        elif isinstance(type_config, dict):
            return type_config.get("enabled", True)
        
        return True
    
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read"""
        try:
            result = await self.db.execute(
                select(Notification).where(
                    and_(
                        Notification.id == uuid.UUID(notification_id),
                        Notification.user_id == uuid.UUID(user_id)
                    )
                )
            )
            notification = result.scalar_one_or_none()
            
            if notification:
                notification.is_read = True
                await self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            await self.db.rollback()
            return False
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for user"""
        try:
            result = await self.db.execute(
                select(Notification).where(
                    and_(
                        Notification.user_id == uuid.UUID(user_id),
                        Notification.is_read == False
                    )
                )
            )
            notifications = result.scalars().all()
            
            count = 0
            for notification in notifications:
                notification.is_read = True
                count += 1
            
            await self.db.commit()
            return count
            
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            await self.db.rollback()
            return 0

