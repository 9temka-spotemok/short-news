"""Legacy adapter for digest domain service."""

from __future__ import annotations

from app.domains.notifications.services.digest_service import DigestService as DomainDigestService


class DigestService(DomainDigestService):
    """Backwards-compatible entry point retained for existing imports."""

    pass


