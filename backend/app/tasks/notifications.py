"""
Notification tasks
"""

import asyncio
from datetime import datetime, timedelta
from celery import current_task
from loguru import logger

from celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models import NewsItem, Notification
from app.services.notification_service import NotificationService
from sqlalchemy import select, and_


@celery_app.task(bind=True)
def process_new_news_notifications(self, news_id: str):
    """
    Process notifications for a newly created news item
    
    Args:
        news_id: ID of the news item
    """
    logger.info(f"Processing notifications for news: {news_id}")
    
    try:
        result = asyncio.run(_process_new_news_notifications_async(news_id))
        logger.info(f"Processed notifications: {result['notifications_created']} created")
        return result
        
    except Exception as e:
        logger.error(f"Failed to process news notifications: {e}")
        raise self.retry(exc=e, countdown=30, max_retries=3)


async def _process_new_news_notifications_async(news_id: str):
    """Async implementation of news notification processing"""
    import uuid
    
    async with AsyncSessionLocal() as db:
        # Get news item
        result = await db.execute(
            select(NewsItem).where(NewsItem.id == uuid.UUID(news_id))
        )
        news_item = result.scalar_one_or_none()
        
        if not news_item:
            return {"status": "error", "message": "News item not found"}
        
        # Check triggers
        notification_service = NotificationService(db)
        notifications = await notification_service.check_new_news_triggers(news_item)
        
        return {
            "status": "success",
            "news_id": news_id,
            "notifications_created": len(notifications)
        }


@celery_app.task(bind=True)
def check_daily_trends(self):
    """
    Check for daily trends and create notifications
    """
    logger.info("Checking daily trends")
    
    try:
        result = asyncio.run(_check_daily_trends_async())
        logger.info(f"Daily trends checked: {result['notifications_created']} notifications")
        return result
        
    except Exception as e:
        logger.error(f"Failed to check daily trends: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _check_daily_trends_async():
    """Async implementation of daily trends checking"""
    async with AsyncSessionLocal() as db:
        notification_service = NotificationService(db)
        
        # Check category trends
        category_notifications = await notification_service.check_category_trends(hours=24, threshold=5)
        
        return {
            "status": "success",
            "notifications_created": len(category_notifications)
        }


@celery_app.task(bind=True)
def check_company_activity(self):
    """
    Check for high company activity and create notifications
    """
    logger.info("Checking company activity")
    
    try:
        result = asyncio.run(_check_company_activity_async())
        logger.info(f"Company activity checked: {result['notifications_created']} notifications")
        return result
        
    except Exception as e:
        logger.error(f"Failed to check company activity: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _check_company_activity_async():
    """Async implementation of company activity checking"""
    async with AsyncSessionLocal() as db:
        notification_service = NotificationService(db)
        
        # Check for companies with 3+ news in last 24 hours
        activity_notifications = await notification_service.check_company_activity(hours=24)
        
        return {
            "status": "success",
            "notifications_created": len(activity_notifications)
        }


@celery_app.task(bind=True)
def cleanup_old_notifications(self):
    """
    Clean up old notifications (older than 30 days)
    """
    logger.info("Starting notification cleanup")
    
    try:
        result = asyncio.run(_cleanup_old_notifications_async())
        logger.info(f"Cleanup completed: {result['deleted_count']} notifications deleted")
        return result
        
    except Exception as e:
        logger.error(f"Failed to cleanup notifications: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _cleanup_old_notifications_async():
    """Async implementation of notification cleanup"""
    async with AsyncSessionLocal() as db:
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Get old notifications
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.created_at < cutoff_date,
                    Notification.is_read == True
                )
            )
        )
        old_notifications = result.scalars().all()
        
        # Delete them
        deleted_count = 0
        for notification in old_notifications:
            await db.delete(notification)
            deleted_count += 1
        
        await db.commit()
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }

