"""
Celery tasks for subscription management
"""

from loguru import logger
from app.celery_app import celery_app
from app.core.celery_async import run_async_task
from app.core.celery_database import CelerySessionLocal
from app.services.subscription_service import SubscriptionService


@celery_app.task(name="subscriptions.check_expired_trials")
def check_expired_trials():
    """
    Periodic task to check and expire trial subscriptions
    
    Runs every hour via Celery Beat
    """
    async def _check_expired_trials():
        async with CelerySessionLocal() as db:
            service = SubscriptionService(db)
            count = await service.expire_trials()
            return count
    
    try:
        count = run_async_task(_check_expired_trials())
        logger.info(f"Checked expired trials: {count} subscriptions expired")
        return {"expired_count": count}
    except Exception as e:
        logger.error(f"Error checking expired trials: {e}", exc_info=True)
        raise


@celery_app.task(name="subscriptions.check_expired_subscriptions")
def check_expired_subscriptions():
    """
    Periodic task to check and expire active subscriptions
    
    Runs every hour via Celery Beat
    """
    async def _check_expired_subscriptions():
        async with CelerySessionLocal() as db:
            service = SubscriptionService(db)
            count = await service.expire_subscriptions()
            return count
    
    try:
        count = run_async_task(_check_expired_subscriptions())
        logger.info(f"Checked expired subscriptions: {count} subscriptions expired")
        return {"expired_count": count}
    except Exception as e:
        logger.error(f"Error checking expired subscriptions: {e}", exc_info=True)
        raise

