"""
Celery application configuration
"""

import asyncio
from celery import Celery
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.crawl_schedule_service import load_effective_celery_schedule

# Create Celery app
celery_app = Celery(
    "shot-news",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.scraping",
        "app.tasks.nlp",
        "app.tasks.digest",
        "app.tasks.notifications",
        "app.tasks.analytics",
        "app.tasks.competitors",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Security settings
    worker_disable_rate_limits=True,
    worker_hijack_root_logger=False,
    # Performance settings
    worker_pool_restarts=True,
    worker_max_memory_per_child=200000,  # 200MB
)

# Base beat schedule definition (will be enriched with dynamic entries)
_BASE_BEAT_SCHEDULE = {
    "scrape-ai-blogs": {
        "task": "app.tasks.scraping.scrape_ai_blogs",
        "schedule": 15 * 60,  # Every 15 minutes
    },
    "fetch-social-media": {
        "task": "app.tasks.scraping.fetch_social_media",
        "schedule": 30 * 60,  # Every 30 minutes
    },
    "monitor-github": {
        "task": "app.tasks.scraping.monitor_github",
        "schedule": 60 * 60,  # Every hour
    },
    "generate-daily-digests": {
        "task": "app.tasks.digest.generate_daily_digests",
        "schedule": 60 * 60,  # Every hour (will check user preferences for timing)
    },
    "generate-weekly-digests": {
        "task": "app.tasks.digest.generate_weekly_digests",
        "schedule": 60 * 60,  # Every hour (will check user preferences for timing)
    },
    "send-channel-digest": {
        "task": "app.tasks.digest.send_channel_digest",
        "schedule": 24 * 60 * 60,  # Daily at midnight UTC
    },
    "check-daily-trends": {
        "task": "app.tasks.notifications.check_daily_trends",
        "schedule": 6 * 60 * 60,  # Every 6 hours
    },
    "check-company-activity": {
        "task": "app.tasks.notifications.check_company_activity",
        "schedule": 4 * 60 * 60,  # Every 4 hours
    },
    "cleanup-old-notifications": {
        "task": "app.tasks.notifications.cleanup_old_notifications",
        "schedule": 24 * 60 * 60,  # Daily
    },
    "dispatch-notification-deliveries": {
        "task": "app.tasks.notifications.dispatch_notification_deliveries",
        "schedule": 60,  # Every minute
    },
    "recompute-analytics-daily": {
        "task": "app.tasks.analytics.recompute_all_analytics",
        "schedule": 6 * 60 * 60,  # Every 6 hours
        "options": {"queue": "analytics"},
    },
    "cleanup-old-data": {
        "task": "app.tasks.scraping.cleanup_old_data",
        "schedule": 24 * 60 * 60,  # Daily
    },
}

try:
    celery_app.conf.beat_schedule = asyncio.run(
        load_effective_celery_schedule(AsyncSessionLocal, _BASE_BEAT_SCHEDULE)
    )
except RuntimeError:
    # Fallback when asyncio.run cannot be invoked (e.g., already within loop)
    celery_app.conf.beat_schedule = _BASE_BEAT_SCHEDULE
except Exception as exc:
    import warnings

    warnings.warn(f"Failed to load dynamic crawl schedule, using defaults: {exc}")
    celery_app.conf.beat_schedule = _BASE_BEAT_SCHEDULE

celery_app.conf.timezone = "UTC"
