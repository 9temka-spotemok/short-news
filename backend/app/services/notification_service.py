"""Legacy adapter for notification domain service."""

from __future__ import annotations

from app.domains.notifications.services.notification_service import (
    NotificationService as DomainNotificationService,
)


class NotificationService(DomainNotificationService):
    """Backwards-compatible entry point retained for existing imports."""

    pass


