"""
Digest generation tasks
"""

from celery import current_task
from loguru import logger

from app.celery_app import celery_app
from app.core.celery_async import run_async_task
from app.core.celery_database import CelerySessionLocal
from app.models import UserPreferences
from app.services.digest_service import DigestService
from app.services.telegram_service import telegram_service
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import pytz
import time
@celery_app.task(bind=True)
def generate_daily_digests(self):
    """
    Generate daily digests for all users
    """
    logger.info("Starting daily digest generation")
    
    try:
        result = run_async_task(_generate_daily_digests_async())
        logger.info(f"Daily digest generation queued: {result['task_count']} tasks")
        return result
        
    except Exception as e:
        logger.error(f"Daily digest generation failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True)
def generate_weekly_digests(self):
    """
    Generate weekly digests for all users
    """
    logger.info("Starting weekly digest generation")
    
    try:
        result = run_async_task(_generate_weekly_digests_async())
        logger.info(f"Weekly digest generation queued: {result['task_count']} tasks")
        return result
        
    except Exception as e:
        logger.error(f"Weekly digest generation failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True)
def generate_user_digest(self, user_id: str, digest_type: str = "daily", tracked_only: bool = False):
    """
    Generate digest for specific user
    """
    logger.info(f"Starting digest generation for user: {user_id}, type: {digest_type}, tracked_only: {tracked_only}")
    
    try:
        result = run_async_task(_generate_user_digest_async(user_id, digest_type, tracked_only))
        logger.info(f"Digest generation completed for user: {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Digest generation failed for user {user_id}: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _generate_daily_digests_async():
    """
    Async implementation of daily digest generation.
    
    Two-phase approach:
    1. Phase 1: Quick selection of users due for digest
    2. Phase 2: Queue individual tasks for parallel processing
    """
    async with CelerySessionLocal() as db:
        # Phase 1: Quick selection of users
        result = await db.execute(
            select(UserPreferences).where(
                UserPreferences.digest_enabled == True,
                UserPreferences.digest_frequency.in_(["daily", "custom"])
            )
        )
        user_prefs_list = result.scalars().all()
        
        logger.info(f"Found {len(user_prefs_list)} users with enabled daily/custom digests")
        
        # Phase 2: Queue individual tasks for parallel processing
        queued_tasks = []
        for user_prefs in user_prefs_list:
            try:
                # Check if user is due for digest now
                if not _is_user_due_now_precise(user_prefs, user_prefs.digest_frequency):
                    continue
                
                # Determine tracked_only based on telegram_digest_mode
                tracked_only = (user_prefs.telegram_digest_mode == 'tracked') if user_prefs.telegram_digest_mode else False
                
                # Queue individual task - will be processed in parallel by workers
                task = generate_user_digest.delay(
                    str(user_prefs.user_id),
                    user_prefs.digest_frequency,
                    tracked_only=tracked_only
                )
                queued_tasks.append(task.id)
                logger.debug(f"Queued digest task for user {user_prefs.user_id} (task_id={task.id})")
                
            except Exception as e:
                logger.error(f"Failed to queue digest for user {user_prefs.user_id}: {e}")
                continue
        
        logger.info(f"Queued {len(queued_tasks)} digest tasks for parallel processing")
        return {"status": "queued", "task_count": len(queued_tasks), "task_ids": queued_tasks}


async def _generate_weekly_digests_async():
    """
    Async implementation of weekly digest generation.
    
    Two-phase approach:
    1. Phase 1: Quick selection of users due for digest
    2. Phase 2: Queue individual tasks for parallel processing
    """
    async with CelerySessionLocal() as db:
        # Phase 1: Quick selection of users
        result = await db.execute(
            select(UserPreferences).where(
                UserPreferences.digest_enabled == True,
                UserPreferences.digest_frequency == "weekly"
            )
        )
        user_prefs_list = result.scalars().all()
        
        logger.info(f"Found {len(user_prefs_list)} users with enabled weekly digests")
        
        # Phase 2: Queue individual tasks for parallel processing
        queued_tasks = []
        for user_prefs in user_prefs_list:
            try:
                # Check if user is due for digest now
                if not _is_user_due_now_precise(user_prefs, "weekly"):
                    continue
                
                # Determine tracked_only based on telegram_digest_mode
                tracked_only = (user_prefs.telegram_digest_mode == 'tracked') if user_prefs.telegram_digest_mode else False
                
                # Queue individual task - will be processed in parallel by workers
                task = generate_user_digest.delay(
                    str(user_prefs.user_id),
                    "weekly",
                    tracked_only=tracked_only
                )
                queued_tasks.append(task.id)
                logger.debug(f"Queued weekly digest task for user {user_prefs.user_id} (task_id={task.id})")
                
            except Exception as e:
                logger.error(f"Failed to queue weekly digest for user {user_prefs.user_id}: {e}")
                continue
        
        logger.info(f"Queued {len(queued_tasks)} weekly digest tasks for parallel processing")
        return {"status": "queued", "task_count": len(queued_tasks), "task_ids": queued_tasks}


async def _generate_user_digest_async(user_id: str, digest_type: str, tracked_only: bool = False):
    """
    Async implementation of user digest generation.
    
    This is called for each user individually, allowing parallel processing.
    """
    start_time = time.perf_counter()
    
    async with CelerySessionLocal() as db:
        # Get user preferences
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        user_prefs = result.scalar_one_or_none()
        
        if not user_prefs:
            logger.warning(f"User preferences not found for user {user_id}")
            return {"status": "error", "message": "User preferences not found"}
        
        # Generate digest
        digest_service = DigestService(db)
        
        # Use provided tracked_only parameter, or fallback to telegram_digest_mode
        if tracked_only is None:
            tracked_only = (user_prefs.telegram_digest_mode == 'tracked') if user_prefs.telegram_digest_mode else False
        
        digest_data = await digest_service.generate_user_digest(
            user_id=user_id,
            period=digest_type,
            format_type=user_prefs.digest_format if user_prefs.digest_format else "short",
            tracked_only=tracked_only
        )
        
        # Send via Telegram if enabled
        if user_prefs.telegram_enabled and user_prefs.telegram_chat_id:
            digest_text = digest_service.format_digest_for_telegram(digest_data, user_prefs)
            await telegram_service.send_digest(user_prefs.telegram_chat_id, digest_text)
            # Show quick controls after sending digest
            await telegram_service.send_post_digest_controls(user_prefs.telegram_chat_id)
            logger.info(f"Digest sent to Telegram for user {user_id} (type: {digest_type}, mode: {user_prefs.telegram_digest_mode or 'all'})")
        
        # Record last sent time (only for scheduled digests, not manual requests)
        # This is safe to do here because generate_user_digest is called both from
        # scheduled tasks and manual requests, but marking is idempotent
        try:
            await _mark_user_sent_now(db, user_prefs)
        except Exception as e:
            logger.warning(f"Failed to mark user {user_id} as sent: {e}")
        
        # Записываем метрику длительности генерации дайджеста
        duration = time.perf_counter() - start_time
        try:
            from app.instrumentation.celery_metrics import _metrics
            _metrics.record_digest_duration(digest_type, duration)
        except Exception:
            pass
        
        return {"status": "success", "user_id": user_id, "digest_type": digest_type, "news_count": digest_data["news_count"]}


# --- Improved scheduling helpers ---
def _parse_user_timezone(user_prefs: UserPreferences):
    tz_name = getattr(user_prefs, "timezone", None) or "UTC"
    try:
        return pytz.timezone(tz_name)
    except Exception:
        logger.warning(f"Unknown timezone '{tz_name}' for user {user_prefs.user_id}; falling back to UTC")
        return pytz.UTC


def _get_schedule_config(user_prefs: UserPreferences) -> dict:
    """Return normalized schedule config from JSON or defaults."""
    cfg = user_prefs.digest_custom_schedule or {}
    return {
        "time": cfg.get("time"),
        "days": cfg.get("days"),
        "timezone": cfg.get("timezone"),
        "last_sent_utc": cfg.get("last_sent_utc"),
    }


def _is_user_due_now_precise(user_prefs: UserPreferences, period: str) -> bool:
    """
    Precise time checking without time windows.
    Sends digest exactly at scheduled time with 1-hour buffer for reliability.
    """
    now_utc = datetime.now(timezone.utc)
    user_tz = _parse_user_timezone(user_prefs)
    now_local = now_utc.astimezone(user_tz)
    
    cfg = _get_schedule_config(user_prefs)
    
    logger.debug(f"Checking digest for user {user_prefs.user_id}, period={period}, timezone={user_tz.zone}")
    logger.debug(f"Current local time: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Check if already sent today
    if _already_sent_today(cfg, now_utc, user_tz):
        logger.debug(f"User {user_prefs.user_id} already sent digest today, skipping")
        return False
    
    # Determine scheduled time
    time_str = cfg.get("time", "09:00")
    try:
        scheduled_h, scheduled_m = map(int, time_str.split(":"))
    except:
        scheduled_h, scheduled_m = 9, 0
    
    logger.debug(f"Scheduled time: {scheduled_h:02d}:{scheduled_m:02d}")
    
    # Check day of week
    current_weekday = now_local.weekday()  # Monday=0, Sunday=6
    current_sunday_based = (current_weekday + 1) % 7  # Sunday=0, Saturday=6
    
    days = cfg.get("days", [])
    
    # Check if today is a valid day for sending
    if period in ["daily", "custom"]:
        day_ok = not days or current_sunday_based in days or current_weekday in days
    elif period == "weekly":
        day_ok = not days or current_sunday_based in days or current_weekday in days
    else:
        day_ok = True
    
    if not day_ok:
        logger.debug(f"Day check failed for user {user_prefs.user_id}: current_day={current_sunday_based}, allowed_days={days}")
        return False
    
    # Precise time check - only if current time >= scheduled time
    scheduled_time = now_local.replace(hour=scheduled_h, minute=scheduled_m, second=0, microsecond=0)
    
    # Send if time has arrived AND not more than 1 hour has passed
    time_passed = (now_local - scheduled_time).total_seconds()
    time_ok = 0 <= time_passed <= 3600  # Within 1 hour after scheduled time
    
    logger.debug(f"Time check: now={now_local.strftime('%H:%M')}, scheduled={scheduled_time.strftime('%H:%M')}, passed={time_passed/60:.1f}min, ok={time_ok}")
    
    result = time_ok
    logger.info(f"Digest check for user {user_prefs.user_id}: period={period}, day_ok={day_ok}, time_ok={time_ok}, result={result}")
    
    return result


def _already_sent_today(cfg: dict, now_utc: datetime, user_tz) -> bool:
    """Check if digest was already sent today"""
    last_sent = cfg.get("last_sent_utc")
    if not last_sent:
        return False
    
    try:
        last_dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
        last_local = last_dt.astimezone(user_tz)
        now_local = now_utc.astimezone(user_tz)
        
        # Compare dates (without time)
        return last_local.date() == now_local.date()
    except:
        return False


async def _mark_user_sent_now(db_session, user_prefs: UserPreferences) -> None:
    """
    Update last sent time and save to database
    """
    cfg = dict(user_prefs.digest_custom_schedule or {})
    cfg["last_sent_utc"] = datetime.now(timezone.utc).isoformat()
    user_prefs.digest_custom_schedule = cfg
    
    try:
        # Save changes to database
        await db_session.commit()
        logger.info(f"Updated last_sent_utc for user {user_prefs.user_id}")
    except Exception as e:
        logger.error(f"Failed to record last_sent_utc for user {user_prefs.user_id}: {e}")
        await db_session.rollback()


@celery_app.task(bind=True)
def send_channel_digest(self):
    """
    Send digest to public Telegram channel
    """
    logger.info("Starting channel digest generation")
    
    try:
        result = run_async_task(_send_channel_digest_async())
        logger.info("Channel digest sent successfully")
        return result
        
    except Exception as e:
        logger.error(f"Channel digest failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _send_channel_digest_async():
    """Async implementation of channel digest"""
    async with CelerySessionLocal() as db:
        # Generate a general digest (top news from all companies)
        digest_service = DigestService(db)
        
        # Get top news from last 24 hours
        from datetime import datetime, timedelta, timezone
        from app.models import NewsItem
        from sqlalchemy import desc
        
        date_from = (datetime.now(timezone.utc) - timedelta(days=1)).replace(tzinfo=None)
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
        now_utc = datetime.now(timezone.utc)
        digest_data = {
            "date_from": date_from.isoformat(),
            "date_to": now_utc.isoformat(),
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