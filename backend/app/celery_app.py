"""
Celery application configuration
"""

import asyncio
import time
import warnings

from celery import Celery
from kombu import Exchange, Queue
from loguru import logger
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
        "app.tasks.reports",
        "app.tasks.observation",
        "app.tasks.subscriptions",
    ]
)

celery_app.conf.task_queues = (
    Queue("celery", Exchange("celery"), routing_key="celery"),
    Queue("analytics", Exchange("analytics"), routing_key="analytics"),
    Queue("telegram", Exchange("telegram"), routing_key="telegram"),
)
celery_app.conf.task_default_queue = "celery"
celery_app.conf.task_routes = {
    "app.tasks.analytics.*": {"queue": "analytics"},
    "app.tasks.digest.generate_user_digest": {"queue": "telegram"},
}

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
    # Broker connection settings - prevent hanging
    broker_connection_timeout=5,  # 5 seconds timeout for broker connection
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=3,
    broker_pool_limit=10,
    # Transport options for Redis broker (prevents hanging)
    broker_transport_options={
        'visibility_timeout': 3600,
        'retry_policy': {
            'timeout': 5.0
        },
        'socket_connect_timeout': 5,  # 5 seconds timeout for socket connection
        'socket_timeout': 5,  # 5 seconds timeout for socket operations
        'socket_keepalive': True,
        'socket_keepalive_options': {},
        'health_check_interval': 30,
    },
)

celery_app.conf.timezone = "UTC"

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
        "schedule": 2 * 60,  # Every 2 minutes
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
    # Observation monitoring periodic tasks
    "periodic-compare-website-structures": {
        "task": "app.tasks.observation.periodic_compare_website_structures",
        "schedule": 24 * 60 * 60,  # Daily
    },
    "periodic-detect-marketing-changes": {
        "task": "app.tasks.observation.periodic_detect_marketing_changes",
        "schedule": 24 * 60 * 60,  # Daily
    },
    "periodic-compare-seo-signals": {
        "task": "app.tasks.observation.periodic_compare_seo_signals",
        "schedule": 7 * 24 * 60 * 60,  # Weekly
    },
    "periodic-scrape-press-releases": {
        "task": "app.tasks.observation.periodic_scrape_press_releases",
        "schedule": 24 * 60 * 60,  # Daily
    },
    # Subscription expiration checks
    "check-expired-trials": {
        "task": "subscriptions.check_expired_trials",
        "schedule": 60 * 60,  # Every hour
    },
    "check-expired-subscriptions": {
        "task": "subscriptions.check_expired_subscriptions",
        "schedule": 60 * 60,  # Every hour
    },
}


def _load_dynamic_schedule_sync(max_retries: int = 3, retry_delay: float = 2.0) -> dict:
    """
    Synchronously load dynamic beat schedule for Celery processes.
    
    Retries on failure to handle cases where database is not ready yet.
    """
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running, create a new one
            try:
                return asyncio.run(
                    load_effective_celery_schedule(AsyncSessionLocal, _BASE_BEAT_SCHEDULE)
                )
            except Exception as exc:
                last_exception = exc
                if attempt < max_retries:
                    logger.debug(
                        "Attempt %d/%d to load dynamic schedule failed, retrying in %.1fs: %s",
                        attempt,
                        max_retries,
                        retry_delay,
                        exc
                    )
                    time.sleep(retry_delay)
                    continue
                break

        # Event loop is running, use run_coroutine_threadsafe
        async def _runner() -> dict:
            return await load_effective_celery_schedule(AsyncSessionLocal, _BASE_BEAT_SCHEDULE)

        try:
            loop = asyncio.get_running_loop()
            return asyncio.run_coroutine_threadsafe(_runner(), loop).result(timeout=10.0)
        except Exception as exc:
            last_exception = exc
            if attempt < max_retries:
                logger.debug(
                    "Attempt %d/%d to load dynamic schedule failed, retrying in %.1fs: %s",
                    attempt,
                    max_retries,
                    retry_delay,
                    exc
                )
                time.sleep(retry_delay)
                continue
            break
    
    # All retries failed, return base schedule
    if last_exception:
        logger.warning(
            "Failed to load dynamic schedule after %d attempts, using base schedule: %s",
            max_retries,
            last_exception
        )
    return _BASE_BEAT_SCHEDULE


@celery_app.on_after_configure.connect
def refresh_dynamic_schedule(sender, **kwargs):
    """Update beat schedule after Celery has been configured."""
    try:
        schedule = _load_dynamic_schedule_sync()
        sender.conf.beat_schedule = schedule
        logger.info(
            "Beat schedule configured with {} task(s)",
            len(schedule)
        )
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "Failed to load dynamic crawl schedule in on_after_configure, using defaults: {}",
            exc,
            exc_info=True
        )
        warnings.warn(f"Failed to load dynamic crawl schedule, using defaults: {exc}")
