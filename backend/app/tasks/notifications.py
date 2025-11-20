"""
Notification tasks
"""

from datetime import datetime, timedelta, timezone

from celery import current_task
from loguru import logger
from sqlalchemy import and_, select

from app.celery_app import celery_app
from app.core.celery_async import run_async_task
from app.core.celery_database import CelerySessionLocal
from app.domains.notifications import NotificationsFacade
from app.models import NewsItem, Notification


@celery_app.task(bind=True)
def process_new_news_notifications(self, news_id: str):
    """
    Process notifications for a newly created news item
    
    Args:
        news_id: ID of the news item
    """
    logger.info(f"Processing notifications for news: {news_id}")
    
    try:
        result = run_async_task(_process_new_news_notifications_async(news_id))
        logger.info(f"Processed notifications: {result['notifications_created']} created")
        return result
        
    except Exception as e:
        logger.error(f"Failed to process news notifications: {e}")
        raise self.retry(exc=e, countdown=30, max_retries=3)


async def _process_new_news_notifications_async(news_id: str):
    """Async implementation of news notification processing"""
    import uuid
    
    async with CelerySessionLocal() as db:
        notifications_facade = NotificationsFacade(db)
        notification_service = notifications_facade.notification_service

        # Get news item
        result = await db.execute(
            select(NewsItem).where(NewsItem.id == uuid.UUID(news_id))
        )
        news_item = result.scalar_one_or_none()
        
        if not news_item:
            return {"status": "error", "message": "News item not found"}
        
        # Check triggers
        created_notifications = await notification_service.check_new_news_triggers(news_item)
        
        return {
            "status": "success",
            "news_id": news_id,
            "notifications_created": len(created_notifications)
        }


@celery_app.task(bind=True)
def check_daily_trends(self):
    """
    Check for daily trends and create notifications
    """
    logger.info("Checking daily trends")
    
    try:
        result = run_async_task(_check_daily_trends_async())
        logger.info(f"Daily trends checked: {result['notifications_created']} notifications")
        return result
        
    except Exception as e:
        logger.error(f"Failed to check daily trends: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _check_daily_trends_async():
    """Async implementation of daily trends checking"""
    async with CelerySessionLocal() as db:
        notifications_facade = NotificationsFacade(db)
        notification_service = notifications_facade.notification_service
        
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
        result = run_async_task(_check_company_activity_async())
        logger.info(f"Company activity checked: {result['notifications_created']} notifications")
        return result
        
    except Exception as e:
        logger.error(f"Failed to check company activity: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _check_company_activity_async():
    """Async implementation of company activity checking"""
    async with CelerySessionLocal() as db:
        notifications_facade = NotificationsFacade(db)
        notification_service = notifications_facade.notification_service
        
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
        result = run_async_task(_cleanup_old_notifications_async())
        logger.info(f"Cleanup completed: {result['deleted_count']} notifications deleted")
        return result
        
    except Exception as e:
        logger.error(f"Failed to cleanup notifications: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _cleanup_old_notifications_async():
    """Async implementation of notification cleanup"""
    async with CelerySessionLocal() as db:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        
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


@celery_app.task(bind=True)
def dispatch_notification_deliveries(self):
    """
    Dispatch pending notification deliveries across channels.
    """
    logger.info("Dispatching pending notification deliveries")

    try:
        result = run_async_task(_dispatch_notification_deliveries_async())
        logger.info(
            "Notification deliveries dispatched: %s sent, %s failed",
            result["sent"],
            result["failed"],
        )
        return result

    except Exception as e:
        logger.error(f"Failed to dispatch notification deliveries: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _dispatch_notification_deliveries_async():
    """Async implementation for dispatching notification deliveries."""
    async with CelerySessionLocal() as db:
        notifications_facade = NotificationsFacade(db)
        dispatcher = notifications_facade.dispatcher
        executor = notifications_facade.delivery_executor

        deliveries = await dispatcher.get_pending_deliveries(limit=25)
        sent = 0
        failed = 0

        for delivery in deliveries:
            success = await executor.process_delivery(delivery)
            if success:
                sent += 1
            else:
                failed += 1

        return {
            "status": "success",
            "sent": sent,
            "failed": failed,
            "total": len(deliveries),
        }



