"""
Notification helpers for competitor change events.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence, Set
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChangeNotificationStatus, Company, CompetitorChangeEvent, User
from app.models.notification_channels import (
    NotificationPriority,
    NotificationType,
)
from app.models.notifications import NotificationSettings
from app.models.preferences import UserPreferences
from app.domains.notifications.services import DispatcherService


class CompetitorNotificationService:
    """Dispatches multi-channel notifications for competitor change events."""

    #: notification TTL in seconds (defaults to 24h window)
    _EVENT_TTL_SECONDS = 24 * 60 * 60

    def __init__(
        self,
        session: AsyncSession,
        *,
        dispatcher: Optional[DispatcherService] = None,
    ) -> None:
        self._session = session
        self._dispatcher = dispatcher or DispatcherService(session)

    async def dispatch_change_event(
        self,
        event: CompetitorChangeEvent | UUID | str,
    ) -> int:
        """Queue notifications for a competitor change event.

        Returns the number of users for whom a notification event was queued.
        """
        event_obj = await self._ensure_event(event)
        if not event_obj:
            logger.warning("Notification dispatch skipped: change event not found (%s)", event)
            return 0

        if event_obj.notification_status == ChangeNotificationStatus.SKIPPED:
            logger.debug(
                "Change event %s already marked as skipped; not dispatching notifications",
                event_obj.id,
            )
            return 0

        watchers = await self._load_watchers(event_obj.company_id)
        if not watchers:
            logger.debug(
                "No subscribed watchers found for company %s; marking change event %s as skipped",
                event_obj.company_id,
                event_obj.id,
            )
            event_obj.notification_status = ChangeNotificationStatus.SKIPPED
            await self._session.commit()
            return 0

        settings_map = await self._load_settings(watchers)
        if not settings_map:
            logger.debug(
                "Watchers for company %s do not have notification settings; skipping notifications",
                event_obj.company_id,
            )
            event_obj.notification_status = ChangeNotificationStatus.SKIPPED
            await self._session.commit()
            return 0

        company_label = await self._company_name(event_obj.company_id)
        payload = self._build_payload(event_obj, company_label)

        dispatched = 0
        for user_id in watchers:
            settings = settings_map.get(user_id)
            if not settings or not settings.enabled:
                continue
            if not self._is_type_enabled(settings, NotificationType.PRICING_CHANGE):
                continue

            result = await self._dispatcher.queue_event(
                user_id=user_id,
                notification_type=NotificationType.PRICING_CHANGE,
                priority=NotificationPriority.HIGH,
                payload={**payload, "user_id": str(user_id)},
                deduplication_key=f"competitor-change:{event_obj.id}:{user_id}",
                ttl_seconds=self._EVENT_TTL_SECONDS,
            )
            if result:
                dispatched += 1

        event_obj.notification_status = (
            ChangeNotificationStatus.SENT if dispatched else ChangeNotificationStatus.SKIPPED
        )
        await self._session.commit()
        logger.debug(
            "Change event %s notification status updated to %s (dispatched=%s)",
            event_obj.id,
            event_obj.notification_status,
            dispatched,
        )
        return dispatched

    async def _ensure_event(
        self,
        event: CompetitorChangeEvent | UUID | str,
    ) -> Optional[CompetitorChangeEvent]:
        if isinstance(event, CompetitorChangeEvent):
            return event

        event_id = UUID(str(event))
        result = await self._session.execute(
            select(CompetitorChangeEvent).where(CompetitorChangeEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def _load_watchers(self, company_id: UUID) -> List[UUID]:
        """
        Load watchers for a company change event.
        Ищет watchers по user_id компаний и subscribed_companies.
        
        ВАЖНО: 
        - Если компания принадлежит пользователю (user_id), он получает уведомление
        - Также ищет пользователей, у которых компания в subscribed_companies
        - Проверяет, что компания действительно принадлежит пользователю или является глобальной
        """
        watchers: List[UUID] = []
        
        # Сначала проверяем, кому принадлежит компания (user_id)
        company_result = await self._session.execute(
            select(Company).where(Company.id == company_id)
        )
        company = company_result.scalar_one_or_none()
        
        if not company:
            logger.warning("Company %s not found, returning empty watchers list", company_id)
            return []
        
        # Если компания принадлежит пользователю (user_id), он должен получить уведомление
        if company.user_id:
            watchers.append(company.user_id)
            logger.debug("Company %s belongs to user %s, added to watchers", company_id, company.user_id)
        
        # Также ищем пользователей, у которых компания в subscribed_companies
        # Но проверяем, что компания действительно принадлежит пользователю или является глобальной
        result = await self._session.execute(select(UserPreferences))
        company_token = str(company_id)
        
        for preferences in result.scalars().all():
            # Пропускаем, если уже добавили этого пользователя (владельца компании)
            if preferences.user_id in watchers:
                continue
            
            companies = self._normalized_company_ids(preferences.subscribed_companies or [])
            if company_token in companies:
                # Проверяем, что компания принадлежит пользователю или является глобальной
                # (не чужая компания)
                if company.user_id is None or company.user_id == preferences.user_id:
                    watchers.append(preferences.user_id)
                    logger.debug(
                        "User %s has company %s in subscribed_companies, added to watchers",
                        preferences.user_id,
                        company_id
                    )
        
        # Удаляем возможные дубликаты с сохранением порядка
        seen: Set[UUID] = set()
        unique_watchers: List[UUID] = []
        for watcher_id in watchers:
            if watcher_id not in seen:
                unique_watchers.append(watcher_id)
                seen.add(watcher_id)
        
        logger.info(
            "Found %d watchers for company %s (owner: %s, subscribers: %d)",
            len(unique_watchers),
            company_id,
            company.user_id if company.user_id else "global",
            len(unique_watchers) - (1 if company.user_id else 0)
        )
        
        return unique_watchers

    async def _load_settings(
        self,
        user_ids: Sequence[UUID],
    ) -> Dict[UUID, NotificationSettings]:
        if not user_ids:
            return {}

        result = await self._session.execute(
            select(NotificationSettings).where(NotificationSettings.user_id.in_(user_ids))
        )
        return {settings.user_id: settings for settings in result.scalars().all()}

    async def _company_name(self, company_id: UUID) -> str:
        result = await self._session.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        return company.name if company and company.name else str(company_id)

    @staticmethod
    def _normalized_company_ids(companies: Iterable[object]) -> Set[str]:
        normalized: Set[str] = set()
        for value in companies:
            if value is None:
                continue
            normalized.add(str(value))
        return normalized

    @staticmethod
    def _is_type_enabled(
        settings: NotificationSettings,
        notification_type: NotificationType,
    ) -> bool:
        if not settings.notification_types:
            return True
        config = settings.notification_types.get(notification_type.value)
        if isinstance(config, bool):
            return config
        if isinstance(config, dict):
            return config.get("enabled", True)
        return True

    @staticmethod
    def _build_payload(
        event: CompetitorChangeEvent,
        company_name: str,
    ) -> Dict[str, object]:
        detected_at = event.detected_at
        if isinstance(detected_at, datetime):
            detected_at_iso = detected_at.isoformat()
        else:
            detected_at_iso = None

        payload: Dict[str, object] = {
            "event_id": str(event.id),
            "company_id": str(event.company_id),
            "company_name": company_name,
            "change_summary": event.change_summary,
            "changed_fields": event.changed_fields or [],
            "raw_diff": event.raw_diff or {},
            "detected_at": detected_at_iso,
        }
        source_type = getattr(event, "source_type", None)
        if hasattr(source_type, "value"):
            payload["source_type"] = source_type.value
        elif source_type is not None:
            payload["source_type"] = str(source_type)
        return payload


__all__ = ["CompetitorNotificationService"]

