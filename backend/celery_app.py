"""
Celery application configuration
"""

from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "shot-news",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.scraping",
        "app.tasks.nlp",
        "app.tasks.digest",
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
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
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
        "schedule": 60 * 60,  # Every hour
    },
    "cleanup-old-data": {
        "task": "app.tasks.scraping.cleanup_old_data",
        "schedule": 24 * 60 * 60,  # Daily
    },
}

celery_app.conf.timezone = "UTC"
