"""Domain service for creating and managing user notifications."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.repositories import (
    NotificationRecordRepository,
    NotificationSettingsRepository,
    UserPreferencesRepository,
)
from app.domains.notifications.services.dispatcher_service import DispatcherService
from app.models import (
    Company,
    NewsItem,
    Notification,
    NotificationPriority,
    NotificationSettings,
    NotificationType,
    UserPreferences,
)
from app.core.access_control import check_company_access


class NotificationService:
    """Domain-level service for in-app notifications."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._notifications = NotificationRecordRepository(session)
        self._settings = NotificationSettingsRepository(session)
        self._preferences = UserPreferencesRepository(session)
        self._dispatcher = DispatcherService(session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def create_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, object]] = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
    ) -> Optional[Notification]:
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            logger.error("Invalid user_id provided to create_notification: %s", user_id)
            return None

        try:
            settings = await self._get_user_settings(user_uuid)
            if not settings or not settings.enabled:
                return None

            if not self._is_type_enabled(settings, notification_type):
                return None

            notification = Notification(
                id=uuid4(),
                user_id=user_uuid,
                type=notification_type,
                title=title,
                message=message,
                data=data or {},
                priority=priority,
                is_read=False,
            )
            notification = await self._notifications.create(notification)

            await self._queue_multi_channel_event(
                notification=notification,
                notification_type=notification_type,
                priority=priority,
                title=title,
                message=message,
                data=data,
            )
            return notification
        except Exception as exc:  # pragma: no cover - logged, rolled back
            logger.error("Error creating notification: %s", exc, exc_info=True)
            await self._session.rollback()
            return None

    async def check_new_news_triggers(self, news_item: NewsItem) -> List[Notification]:
        notifications: List[Notification] = []
        settings_list = await self._settings.list_enabled()

        for settings in settings_list:
            user_prefs = await self._preferences.get(settings.user_id)
            if not user_prefs:
                continue

            notification_type, priority, should_notify = await self._evaluate_news_match(
                news_item=news_item,
                settings=settings,
                preferences=user_prefs,
            )

            if not should_notify:
                continue

            company_name = "Unknown"
            if news_item.company_id:
                company = await self._get_company(news_item.company_id)
                if company:
                    company_name = company.name

            notification = await self.create_notification(
                user_id=str(settings.user_id),
                notification_type=notification_type,
                title=f"{company_name}: {news_item.category or 'News'}",
                message=news_item.title,
                data={
                    "news_id": str(news_item.id),
                    "company_id": str(news_item.company_id) if news_item.company_id else None,
                    "category": news_item.category,
                    "source_url": news_item.source_url,
                },
                priority=priority,
            )
            if notification:
                notifications.append(notification)

        return notifications

    async def check_company_activity(self, hours: int = 24) -> List[Notification]:
        notifications: List[Notification] = []
        cutoff_time_aware = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_time = cutoff_time_aware.replace(tzinfo=None)

        result = await self._session.execute(
            select(NewsItem.company_id, func.count(NewsItem.id).label("count"))
            .where(NewsItem.published_at >= cutoff_time)
            .group_by(NewsItem.company_id)
            .having(func.count(NewsItem.id) >= 3)
        )
        active_companies = result.all()

        for company_id, news_count in active_companies:
            if not company_id:
                continue

            user_prefs_list = await self._preferences.list_subscribed_to_company(company_id)
            for user_prefs in user_prefs_list:
                settings = await self._get_user_settings(user_prefs.user_id)
                if not settings or not settings.enabled or not settings.company_alerts:
                    continue

                company = await self._get_company(company_id)
                if not company:
                    continue

                notification = await self.create_notification(
                    user_id=str(user_prefs.user_id),
                    notification_type=NotificationType.COMPANY_ACTIVE,
                    title=f"High Activity: {company.name}",
                    message=(
                        f"{company.name} has published {news_count} news items "
                        f"in the last {hours} hours"
                    ),
                    data={
                        "company_id": str(company_id),
                        "news_count": news_count,
                        "hours": hours,
                    },
                    priority=NotificationPriority.MEDIUM,
                )
                if notification:
                    notifications.append(notification)

        return notifications

    async def check_category_trends(
        self,
        hours: int = 24,
        threshold: int = 5,
    ) -> List[Notification]:
        notifications: List[Notification] = []
        cutoff_time_aware = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_time = cutoff_time_aware.replace(tzinfo=None)

        result = await self._session.execute(
            select(NewsItem.category, func.count(NewsItem.id).label("count"))
            .where(NewsItem.published_at >= cutoff_time)
            .group_by(NewsItem.category)
            .having(func.count(NewsItem.id) >= threshold)
        )
        trending_categories = result.all()

        for category, news_count in trending_categories:
            if not category:
                continue
            # Normalize category to lowercase to match enum values in database
            # Enum values in PostgreSQL are stored as lowercase (e.g., 'product_update')
            category_normalized = str(category).lower() if category else None
            if not category_normalized:
                continue
            user_prefs_list = await self._preferences.list_interested_in_category(category_normalized)

            for user_prefs in user_prefs_list:
                settings = await self._get_user_settings(user_prefs.user_id)
                if not settings or not settings.enabled or not settings.category_trends:
                    continue

                notification = await self.create_notification(
                    user_id=str(user_prefs.user_id),
                    notification_type=NotificationType.CATEGORY_TREND,
                    title=f"Trending: {category_normalized.replace('_', ' ').title()}",
                    message=(
                        f"{news_count} news items in {category_normalized.replace('_', ' ')} "
                        f"category in the last {hours} hours"
                    ),
                    data={
                        "category": category_normalized,
                        "news_count": news_count,
                        "hours": hours,
                    },
                    priority=NotificationPriority.LOW,
                )
                if notification:
                    notifications.append(notification)

        return notifications

    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        try:
            notification = await self._notifications.get_for_user(
                notification_id=UUID(notification_id),
                user_id=UUID(user_id),
            )
            if not notification:
                return False

            await self._notifications.mark_as_read(notification)
            return True
        except Exception as exc:  # pragma: no cover
            logger.error("Error marking notification as read: %s", exc, exc_info=True)
            await self._session.rollback()
            return False

    async def mark_all_as_read(self, user_id: str) -> int:
        try:
            return await self._notifications.mark_all_as_read(UUID(user_id))
        except Exception as exc:  # pragma: no cover
            logger.error("Error marking notifications as read: %s", exc, exc_info=True)
            await self._session.rollback()
            return 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _queue_multi_channel_event(
        self,
        *,
        notification: Notification,
        notification_type: NotificationType,
        priority: NotificationPriority,
        title: str,
        message: str,
        data: Optional[Dict[str, object]],
    ) -> None:
        try:
            dedup_key = None
            if data:
                dedup_key = data.get("news_id") or data.get("company_id")
            await self._dispatcher.queue_event(
                user_id=notification.user_id,
                notification_type=notification_type,
                priority=priority,
                payload={
                    "title": title,
                    "message": message,
                    **(data or {}),
                },
                deduplication_key=dedup_key,
            )
        except Exception as dispatch_error:  # pragma: no cover
            logger.error(
                "Failed to queue multi-channel notification event: %s",
                dispatch_error,
                exc_info=True,
            )

    async def _get_user_settings(self, user_id: UUID) -> Optional[NotificationSettings]:
        return await self._settings.get(user_id)

    async def _get_company(self, company_id: UUID) -> Optional[Company]:
        result = await self._session.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def _get_user_preferences(self, user_id: UUID) -> Optional[UserPreferences]:
        return await self._preferences.get(user_id)

    def _is_type_enabled(
        self,
        settings: NotificationSettings,
        notification_type: NotificationType,
    ) -> bool:
        if not settings.notification_types:
            return True

        config = settings.notification_types.get(notification_type.value, {})
        if isinstance(config, bool):
            return config
        if isinstance(config, dict):
            return config.get("enabled", True)
        return True

    async def _evaluate_news_match(
        self,
        *,
        news_item: NewsItem,
        settings: NotificationSettings,
        preferences: UserPreferences,
    ) -> tuple[NotificationType, NotificationPriority, bool]:
        """
        Evaluate if news item should trigger notification.
        Проверяет, должна ли новость вызвать уведомление.
        
        ВАЖНО: Сначала проверяет, что компания принадлежит пользователю (user_id),
        затем проверяет subscribed_companies.
        """
        should_notify = False
        notification_type = NotificationType.NEW_NEWS
        priority = NotificationPriority.MEDIUM

        # СНАЧАЛА проверяем, что компания принадлежит пользователю (user_id)
        if news_item.company_id:
            from app.models import User
            user = await self._session.get(User, preferences.user_id)
            if user:
                company = await check_company_access(news_item.company_id, user, self._session)
                if not company:
                    # Компания не принадлежит пользователю - не отправляем уведомление
                    logger.debug(
                        "Company %s does not belong to user %s, skipping notification",
                        news_item.company_id,
                        preferences.user_id
                    )
                    return notification_type, priority, False

        # Company-based alerts (только для subscribed_companies, которые принадлежат пользователю)
        if settings.company_alerts and preferences.subscribed_companies:
            if news_item.company_id in preferences.subscribed_companies:
                should_notify = True

                if news_item.category == "pricing_change":
                    notification_type = NotificationType.PRICING_CHANGE
                    priority = NotificationPriority.HIGH
                elif news_item.category == "funding_news":
                    notification_type = NotificationType.FUNDING_ANNOUNCEMENT
                    priority = NotificationPriority.HIGH
                elif news_item.category == "product_update":
                    notification_type = NotificationType.PRODUCT_LAUNCH
                    priority = NotificationPriority.MEDIUM

        # Keyword-based alerts (тоже только для компаний пользователя)
        if settings.keyword_alerts and preferences.keywords:
            title = (news_item.title or "").lower()
            content = (news_item.content or "").lower()
            for keyword in preferences.keywords:
                lowered = keyword.lower()
                if lowered in title or lowered in content:
                    should_notify = True
                    notification_type = NotificationType.KEYWORD_MATCH
                    priority = NotificationPriority.HIGH
                    break

        # Priority score threshold
        if should_notify and settings.min_priority_score:
            if (news_item.priority_score or 0) < settings.min_priority_score:
                should_notify = False

        return notification_type, priority, should_notify


