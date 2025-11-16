"""
Legacy module retained for backwards compatibility.

The analytics snapshot logic now lives under `app.domains.analytics`. Import
`AnalyticsService` from here to keep existing code working during the migration.
"""

from app.domains.analytics.services.snapshot_service import SnapshotService as AnalyticsService

__all__ = ["AnalyticsService"]
