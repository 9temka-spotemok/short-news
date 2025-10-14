"""
Digest generation tasks
"""

import asyncio
from celery import current_task
from loguru import logger

from celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models import UserPreferences
from app.services.digest_service import DigestService
from app.services.telegram_service import telegram_service
from sqlalchemy import select


@celery_app.task(bind=True)
def generate_daily_digests(self):
    """
    Generate daily digests for all users
    """
    logger.info("Starting daily digest generation")
    
    try:
        # Run async function
        result = asyncio.run(_generate_daily_digests_async())
        logger.info(f"Daily digest generation completed: {result['generated_count']} digests")
        return result
        
    except Exception as e:
        logger.error(f"Daily digest generation failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _generate_daily_digests_async():
    """Async implementation of daily digest generation"""
    async with AsyncSessionLocal() as db:
        # Get all users with digest enabled and daily frequency
        result = await db.execute(
            select(UserPreferences).where(
                UserPreferences.digest_enabled == True,
                UserPreferences.digest_frequency == "daily"
            )
        )
        user_prefs_list = result.scalars().all()
        
        generated_count = 0
        for user_prefs in user_prefs_list:
            try:
                # Generate digest
                digest_service = DigestService(db)
                digest_data = await digest_service.generate_user_digest(
                    user_id=str(user_prefs.user_id),
                    period="daily",
                    format_type=user_prefs.digest_format.value if user_prefs.digest_format else "short"
                )
                
                # Send via Telegram if enabled
                if user_prefs.telegram_enabled and user_prefs.telegram_chat_id:
                    digest_text = digest_service.format_digest_for_telegram(digest_data)
                    await telegram_service.send_digest(user_prefs.telegram_chat_id, digest_text)
                    logger.info(f"Digest sent to Telegram for user {user_prefs.user_id}")
                
                generated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to generate digest for user {user_prefs.user_id}: {e}")
                continue
        
        return {"status": "success", "generated_count": generated_count}


@celery_app.task(bind=True)
def generate_user_digest(self, user_id: str, digest_type: str = "daily"):
    """
    Generate digest for specific user
    """
    logger.info(f"Starting digest generation for user: {user_id}, type: {digest_type}")
    
    try:
        result = asyncio.run(_generate_user_digest_async(user_id, digest_type))
        logger.info(f"Digest generation completed for user: {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Digest generation failed for user {user_id}: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _generate_user_digest_async(user_id: str, digest_type: str):
    """Async implementation of user digest generation"""
    async with AsyncSessionLocal() as db:
        # Get user preferences
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        user_prefs = result.scalar_one_or_none()
        
        if not user_prefs:
            return {"status": "error", "message": "User preferences not found"}
        
        # Generate digest
        digest_service = DigestService(db)
        digest_data = await digest_service.generate_user_digest(
            user_id=user_id,
            period=digest_type,
            format_type=user_prefs.digest_format.value if user_prefs.digest_format else "short"
        )
        
        # Send via Telegram if enabled
        if user_prefs.telegram_enabled and user_prefs.telegram_chat_id:
            digest_text = digest_service.format_digest_for_telegram(digest_data)
            await telegram_service.send_digest(user_prefs.telegram_chat_id, digest_text)
        
        return {"status": "success", "user_id": user_id, "digest_type": digest_type, "news_count": digest_data["news_count"]}


@celery_app.task(bind=True)
def send_channel_digest(self):
    """
    Send digest to public Telegram channel
    """
    logger.info("Starting channel digest generation")
    
    try:
        result = asyncio.run(_send_channel_digest_async())
        logger.info("Channel digest sent successfully")
        return result
        
    except Exception as e:
        logger.error(f"Channel digest failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _send_channel_digest_async():
    """Async implementation of channel digest"""
    async with AsyncSessionLocal() as db:
        # Generate a general digest (top news from all companies)
        digest_service = DigestService(db)
        
        # Create a mock user preference for general digest
        from app.models.preferences import UserPreferences
        import uuid
        
        # Get top news from last 24 hours
        from datetime import datetime, timedelta
        from app.models import NewsItem
        from sqlalchemy import desc
        
        date_from = datetime.utcnow() - timedelta(days=1)
        result = await db.execute(
            select(NewsItem)
            .where(NewsItem.published_at >= date_from)
            .order_by(desc(NewsItem.priority_score), desc(NewsItem.published_at))
            .limit(20)
        )
        top_news = list(result.scalars().all())
        
        if not top_news:
            logger.info("No news for channel digest")
            return {"status": "success", "message": "No news to send"}
        
        # Format for Telegram
        digest_data = {
            "date_from": date_from.isoformat(),
            "date_to": datetime.utcnow().isoformat(),
            "news_count": len(top_news),
            "categories": {},
            "format": "short"
        }
        
        # Group by category
        for news in top_news:
            category = news.category or "uncategorized"
            if category not in digest_data["categories"]:
                digest_data["categories"][category] = []
            
            digest_data["categories"][category].append({
                "id": str(news.id),
                "title": news.title,
                "source_url": news.source_url,
                "published_at": news.published_at.isoformat()
            })
        
        digest_text = digest_service.format_digest_for_telegram(digest_data)
        await telegram_service.send_to_channel(digest_text)
        
        return {"status": "success", "news_count": len(top_news)}
