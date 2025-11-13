"""
Telegram webhook endpoints
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger
import json
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.services.telegram_service import telegram_service
from app.bot.handlers import handle_message
from app.models import UserPreferences, User
from app.tasks.digest import generate_user_digest
from sqlalchemy import select, func

router = APIRouter()

# Simple in-memory cache for user preferences (expires after 5 minutes)
_user_prefs_cache = {}
_cache_expiry = {}

def _get_cached_user_prefs(chat_id: str) -> Optional[UserPreferences]:
    """Get cached user preferences if not expired"""
    if chat_id in _user_prefs_cache and chat_id in _cache_expiry:
        expiry = _cache_expiry[chat_id]
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
            _cache_expiry[chat_id] = expiry
        if datetime.now(timezone.utc) < expiry:
            return _user_prefs_cache[chat_id]
        else:
            # Remove expired cache
            del _user_prefs_cache[chat_id]
            del _cache_expiry[chat_id]
    return None

def _cache_user_prefs(chat_id: str, user_prefs: UserPreferences):
    """Cache user preferences for 5 minutes"""
    _user_prefs_cache[chat_id] = user_prefs
    _cache_expiry[chat_id] = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=5)


class TelegramWebhookUpdate(BaseModel):
    """Telegram webhook update model"""
    update_id: int
    message: Optional[Dict[str, Any]] = None
    edited_message: Optional[Dict[str, Any]] = None
    channel_post: Optional[Dict[str, Any]] = None
    edited_channel_post: Optional[Dict[str, Any]] = None
    inline_query: Optional[Dict[str, Any]] = None
    chosen_inline_result: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None


@router.get("/webhook")
async def telegram_webhook_health_check():
    """
    Health check endpoint for Telegram webhook
    Telegram sends POST requests, but GET can be used for checking if endpoint is accessible
    """
    return {
        "status": "ok",
        "message": "Telegram webhook endpoint is active. Use POST method for webhook updates.",
        "endpoint": "/api/v1/telegram/webhook",
        "method": "POST"
    }


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Telegram webhook updates
    """
    try:
        # Parse webhook data
        body = await request.json()
        logger.info(f"Received Telegram webhook: {json.dumps(body, indent=2)}")
        
        update = TelegramWebhookUpdate(**body)
        
        # Handle different types of updates
        if update.message:
            await handle_telegram_message(update.message, db)
        elif update.callback_query:
            await handle_telegram_callback(update.callback_query, db)
        elif update.channel_post:
            await handle_channel_post(update.channel_post, db)
        else:
            logger.info(f"Unhandled update type: {update}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error handling Telegram webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


async def handle_telegram_message(message: Dict[str, Any], db: AsyncSession):
    """Handle incoming Telegram message"""
    try:
        chat_id = str(message["chat"]["id"])
        text = message.get("text", "")
        username = message.get("from", {}).get("username")
        first_name = message.get("from", {}).get("first_name", "")
        
        logger.info(f"Processing message from {chat_id} ({username}): {text}")
        
        # Handle the message using our bot handlers
        response = await handle_message(chat_id, text, username)
        
        # Send response back to user
        await telegram_service.send_digest(chat_id, response)
        
        # Previously /digest generated digest immediately. Now /digest opens settings menu.
        # Generation is triggered by buttons (digest_daily/digest_weekly).
            
    except Exception as e:
        logger.error(f"Error handling Telegram message: {e}")


async def handle_telegram_callback(callback_query: Dict[str, Any], db: AsyncSession):
    """Handle Telegram callback queries (inline keyboard buttons)"""
    try:
        chat_id = str(callback_query["message"]["chat"]["id"])
        data = callback_query.get("data", "")
        
        logger.info(f"Processing callback from {chat_id}: {data}")
        
        # Handle different callback types
        # IMPORTANT: Check more specific prefixes FIRST to avoid conflicts!
        if data.startswith("digest_settings_"):
            # Handle digest settings mode change (all/tracked) or show menu (settings_digest)
            if data in ["digest_settings_all", "digest_settings_tracked"]:
                logger.info(f"Routing to handle_digest_mode_change: {data}")
                await handle_digest_mode_change(chat_id, data, db)
            else:
                # Show settings menu
                await handle_digest_settings_menu(chat_id, db)
        elif data.startswith("digest_"):
            await handle_digest_callback(chat_id, data, db)
        elif data.startswith("settings_"):
            await handle_settings_callback(chat_id, data, db)
        elif data == "help":
            await handle_help_callback(chat_id, db)
        elif data == "main_menu":
            await handle_main_menu_callback(chat_id, db)
        
        # Answer callback query to remove loading state
        await telegram_service.answer_callback_query(callback_query["id"])
        
    except Exception as e:
        logger.error(f"Error handling Telegram callback: {e}", exc_info=True)


async def handle_channel_post(channel_post: Dict[str, Any], db: AsyncSession):
    """Handle channel posts (for public channel)"""
    logger.info(f"Channel post received: {channel_post}")
    # Channel posts are usually from other admins, we don't need to respond


async def handle_digest_command_real(chat_id: str, db: AsyncSession):
    """Handle real /digest command - find user and trigger digest generation"""
    try:
        # Normalize chat_id - remove whitespace
        chat_id_clean = chat_id.strip()
        
        # Find user by telegram_chat_id (using trim to handle any whitespace issues)
        result = await db.execute(
            select(UserPreferences).where(
                func.trim(UserPreferences.telegram_chat_id) == chat_id_clean,
                UserPreferences.telegram_enabled == True
            )
        )
        user_prefs = result.scalars().first()
        
        # If not found, try without trim (fallback)
        if not user_prefs:
            result = await db.execute(
                select(UserPreferences).where(
                    UserPreferences.telegram_chat_id == chat_id_clean,
                    UserPreferences.telegram_enabled == True
                )
            )
            user_prefs = result.scalars().first()
        
        if not user_prefs:
            # Log diagnostic info
            result_debug = await db.execute(
                select(UserPreferences).where(
                    func.trim(UserPreferences.telegram_chat_id) == chat_id_clean
                )
            )
            user_prefs_debug = result_debug.scalars().first()
            
            logger.warning(
                f"User not found for chat_id={chat_id_clean}. "
                f"Found user without enabled check: {user_prefs_debug.user_id if user_prefs_debug else 'None'}. "
                f"telegram_enabled={user_prefs_debug.telegram_enabled if user_prefs_debug else 'N/A'}"
            )
            
            # User not found or Telegram not enabled
            await telegram_service.send_digest(
                chat_id, 
                "❌ User not found or Telegram not configured.\n\n"
                "Make sure you:\n"
                "1. Added Chat ID to your profile settings\n"
                "2. Enabled Telegram notifications\n"
                "3. Configured digests\n\n"
                f"Your Chat ID: `{chat_id_clean}`"
            )
            return
        
        # Trigger digest generation
        task = generate_user_digest.delay(str(user_prefs.user_id), "daily")
        
        await telegram_service.send_digest(
            chat_id,
            "📰 Digest is generating...\n\n"
            "Your personalized digest will be sent shortly!"
        )
        
        logger.info(f"Digest generation triggered for user {user_prefs.user_id}")
        
    except Exception as e:
        logger.error(f"Error handling real digest command: {e}")
        await telegram_service.send_digest(
            chat_id,
            "❌ Error generating digest. Please try again later."
        )


async def handle_digest_callback(chat_id: str, data: str, db: AsyncSession):
    """Handle digest-related callback queries"""
    from app.tasks.digest import generate_user_digest
    from sqlalchemy import select
    
    logger.info(f"handle_digest_callback called: chat_id={chat_id}, data={data}")
    
    try:
        # Normalize chat_id - remove whitespace
        chat_id_clean = chat_id.strip()
        logger.debug(f"Normalized chat_id: '{chat_id_clean}'")
        
        # Try to get cached user preferences first
        user_prefs = _get_cached_user_prefs(chat_id_clean)
        cache_source = "cache"
        
        if not user_prefs:
            cache_source = "database"
            # Expire all cached data to ensure we get fresh data from database
            # This is important because telegram_digest_mode might have been updated in another transaction
            db.expire_all()
            
            # Find user by telegram_chat_id (using trim to handle any whitespace issues)
            result = await db.execute(
                select(UserPreferences).where(
                    func.trim(UserPreferences.telegram_chat_id) == chat_id_clean,
                    UserPreferences.telegram_enabled == True
                )
            )
            user_prefs = result.scalars().first()
            
            # If not found, try without trim (fallback)
            if not user_prefs:
                result = await db.execute(
                    select(UserPreferences).where(
                        UserPreferences.telegram_chat_id == chat_id_clean,
                        UserPreferences.telegram_enabled == True
                    )
                )
                user_prefs = result.scalars().first()
            
            if user_prefs:
                _cache_user_prefs(chat_id_clean, user_prefs)
        
        if not user_prefs:
            # Log diagnostic info
            result_debug = await db.execute(
                select(UserPreferences).where(
                    func.trim(UserPreferences.telegram_chat_id) == chat_id_clean
                )
            )
            user_prefs_debug = result_debug.scalars().first()
            
            logger.warning(
                f"User not found for chat_id={chat_id_clean} in digest callback. "
                f"Found user without enabled check: {user_prefs_debug.user_id if user_prefs_debug else 'None'}. "
                f"telegram_enabled={user_prefs_debug.telegram_enabled if user_prefs_debug else 'N/A'}"
            )
            
            message_sent = await telegram_service.send_digest(
                chat_id,
                "❌ User not found or Telegram not configured.\n\n"
                "Make sure you:\n"
                "1. Added Chat ID to your profile settings\n"
                "2. Enabled Telegram notifications\n"
                "3. Configured digests\n\n"
                f"Your Chat ID: `{chat_id_clean}`"
            )
            if not message_sent:
                logger.error(f"Failed to send error message to chat_id={chat_id_clean}")
            return
        
        if data == "digest_daily":
            # Determine tracked_only based on telegram_digest_mode
            tracked_only = (user_prefs.telegram_digest_mode == 'tracked') if user_prefs.telegram_digest_mode else False
            
            logger.info(f"Daily digest for user {user_prefs.user_id}: source={cache_source}, telegram_digest_mode={user_prefs.telegram_digest_mode}, tracked_only={tracked_only}")
            
            task = generate_user_digest.delay(str(user_prefs.user_id), "daily", tracked_only=tracked_only)
            mode_text = "tracked companies only" if tracked_only else "all news"
            message_sent = await telegram_service.send_digest(
                chat_id,
                f"📅 Daily digest ({mode_text}) is generating...\n\n"
                "Your personalized digest will be sent shortly!"
            )
            if not message_sent:
                logger.error(f"Failed to send 'generating' message to chat_id={chat_id} for daily digest")
            
        elif data == "digest_weekly":
            # Determine tracked_only based on telegram_digest_mode
            tracked_only = (user_prefs.telegram_digest_mode == 'tracked') if user_prefs.telegram_digest_mode else False
            
            logger.info(f"Weekly digest for user {user_prefs.user_id}: source={cache_source}, telegram_digest_mode={user_prefs.telegram_digest_mode}, tracked_only={tracked_only}")
            
            task = generate_user_digest.delay(str(user_prefs.user_id), "weekly", tracked_only=tracked_only)
            mode_text = "tracked companies only" if tracked_only else "all news"
            message_sent = await telegram_service.send_digest(
                chat_id,
                f"📊 Weekly digest ({mode_text}) is generating...\n\n"
                "Your personalized digest will be sent shortly!"
            )
            if not message_sent:
                logger.error(f"Failed to send 'generating' message to chat_id={chat_id} for weekly digest")
            
        elif data == "settings_digest":
            await handle_digest_settings_menu(chat_id, db)
            
    except Exception as e:
        logger.error(f"Error handling digest callback: {e}", exc_info=True)
        message_sent = await telegram_service.send_digest(
            chat_id,
            "❌ Error generating digest. Please try again later."
        )
        if not message_sent:
            logger.error(f"Failed to send error message to chat_id={chat_id} after exception")


async def handle_digest_settings_menu(chat_id: str, db: AsyncSession):
    """Handle digest settings menu display"""
    try:
        # Normalize chat_id - remove whitespace
        chat_id_clean = chat_id.strip()
        
        # Expire all cached data to ensure we get fresh data from database
        db.expire_all()
        
        # Find user by telegram_chat_id (using trim to handle any whitespace issues)
        result = await db.execute(
            select(UserPreferences).where(
                func.trim(UserPreferences.telegram_chat_id) == chat_id_clean,
                UserPreferences.telegram_enabled == True
            )
        )
        user_prefs = result.scalars().first()
        
        # If not found, try without trim (fallback)
        if not user_prefs:
            result = await db.execute(
                select(UserPreferences).where(
                    UserPreferences.telegram_chat_id == chat_id_clean,
                    UserPreferences.telegram_enabled == True
                )
            )
            user_prefs = result.scalars().first()
        
        if user_prefs:
            current_mode = user_prefs.telegram_digest_mode or 'all'
            await telegram_service.send_digest_settings_menu(chat_id_clean, current_mode)
        else:
            await telegram_service.send_digest(
                chat_id_clean,
                "❌ User not found. Use /start to configure."
            )
        
    except Exception as e:
        logger.error(f"Error handling digest settings menu: {e}")
        await telegram_service.send_digest(
            chat_id,
            "❌ Error getting settings. Please try again later."
        )


async def handle_settings_callback(chat_id: str, data: str, db: AsyncSession):
    """Handle settings-related callback queries"""
    # Normalize chat_id - remove whitespace
    chat_id_clean = chat_id.strip()
    
    if data == "settings_view":
        # Show current settings
        # Expire all cached data to ensure we get fresh data from database
        db.expire_all()
        
        # Find user by telegram_chat_id (using trim to handle any whitespace issues)
        result = await db.execute(
            select(UserPreferences).where(
                func.trim(UserPreferences.telegram_chat_id) == chat_id_clean,
                UserPreferences.telegram_enabled == True
            )
        )
        user_prefs = result.scalars().first()
        
        # If not found, try without trim (fallback)
        if not user_prefs:
            result = await db.execute(
                select(UserPreferences).where(
                    UserPreferences.telegram_chat_id == chat_id_clean,
                    UserPreferences.telegram_enabled == True
                )
            )
            user_prefs = result.scalars().first()
        
        if user_prefs:
            settings_text = f"""
⚙️ **Your Settings:**

📊 Digests: {'✅ Enabled' if user_prefs.digest_enabled else '❌ Disabled'}
📅 Frequency: {user_prefs.digest_frequency.value if user_prefs.digest_frequency else 'Not configured'}
📝 Format: {user_prefs.digest_format.value if user_prefs.digest_format else 'Not configured'}
🌐 Timezone: {user_prefs.timezone if hasattr(user_prefs, 'timezone') else 'UTC'}

Use the web application to change settings.
            """
            await telegram_service.send_digest(chat_id_clean, settings_text)
        else:
            await telegram_service.send_digest(
                chat_id_clean,
                "❌ User not found. Use /start to configure."
            )
    
    elif data == "settings_digest":
        # Show digest settings menu
        await handle_digest_settings_menu(chat_id_clean, db)


async def handle_digest_mode_change(chat_id: str, data: str, db: AsyncSession):
    """Handle digest mode change (all/tracked)"""
    logger.info(f"handle_digest_mode_change called: chat_id={chat_id}, data={data}")
    try:
        # Normalize chat_id - remove whitespace
        chat_id_clean = chat_id.strip()
        logger.debug(f"Normalized chat_id: '{chat_id_clean}'")
        
        # Expire all cached data to ensure we get fresh data from database
        db.expire_all()
        
        # Find user by telegram_chat_id (using trim to handle any whitespace issues)
        result = await db.execute(
            select(UserPreferences).where(
                func.trim(UserPreferences.telegram_chat_id) == chat_id_clean,
                UserPreferences.telegram_enabled == True
            )
        )
        user_prefs = result.scalars().first()
        
        # If not found, try without trim (fallback)
        if not user_prefs:
            result = await db.execute(
                select(UserPreferences).where(
                    UserPreferences.telegram_chat_id == chat_id_clean,
                    UserPreferences.telegram_enabled == True
                )
            )
            user_prefs = result.scalars().first()
        
        if not user_prefs:
            await telegram_service.send_digest(
                chat_id_clean, 
                "❌ User not found. Use /start to configure."
            )
            return
        
        # Determine new mode
        if data == "digest_settings_all":
            new_mode = "all"
        elif data == "digest_settings_tracked":
            new_mode = "tracked"
        else:
            await telegram_service.send_digest(chat_id_clean, "❌ Unknown setting.")
            return
        
        # Update via ORM assignment against the correct enum type
        user_prefs.telegram_digest_mode = new_mode
        await db.commit()
        await db.refresh(user_prefs)

        # Invalidate cached preferences for this chat to ensure new mode is used immediately
        try:
            if chat_id_clean in _user_prefs_cache:
                del _user_prefs_cache[chat_id_clean]
            if chat_id_clean in _cache_expiry:
                del _cache_expiry[chat_id_clean]
        except Exception:
            pass
        
        # Send confirmation and updated menu
        confirmation_text = f"✅ Setting changed to: **{'All News' if new_mode == 'all' else 'Tracked Only'}**"
        confirmation_sent = await telegram_service.send_digest(chat_id_clean, confirmation_text)
        if not confirmation_sent:
            logger.error(f"Failed to send confirmation message to chat_id={chat_id_clean}")
        
        # Show updated settings menu
        menu_sent = await telegram_service.send_digest_settings_menu(chat_id_clean, new_mode)
        if not menu_sent:
            logger.error(f"Failed to send settings menu to chat_id={chat_id_clean}")
        
        logger.info(f"Digest mode changed to {new_mode} for user {user_prefs.user_id} (chat_id: {chat_id_clean})")
        
    except Exception as e:
        logger.error(f"Error handling digest mode change: {e}", exc_info=True)
        error_message_sent = await telegram_service.send_digest(
            chat_id,
            "❌ Error changing settings. Please try again later."
        )
        if not error_message_sent:
            logger.error(f"Failed to send error message to chat_id={chat_id} after exception")


@router.get("/set-webhook")
async def set_telegram_webhook(
    webhook_url: str = "https://yourdomain.com/api/v1/telegram/webhook"
):
    """
    Set Telegram webhook URL
    """
    try:
        success = await telegram_service.set_webhook(webhook_url)
        if success:
            return {"status": "success", "webhook_url": webhook_url}
        else:
            raise HTTPException(status_code=500, detail="Failed to set webhook")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/delete-webhook")
async def delete_telegram_webhook():
    """
    Delete Telegram webhook
    """
    try:
        success = await telegram_service.delete_webhook()
        if success:
            return {"status": "success", "message": "Webhook deleted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete webhook")
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get-webhook-info")
async def get_webhook_info():
    """
    Get current webhook information
    """
    try:
        info = await telegram_service.get_webhook_info()
        return {"status": "success", "webhook_info": info}
    except Exception as e:
        logger.error(f"Error getting webhook info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-test-message")
async def send_test_message(
    chat_id: str,
    message: str = "🧪 Test message from AI Competitor Insight Hub"
):
    """
    Send test message to specified chat
    """
    try:
        success = await telegram_service.send_digest(chat_id, message)
        if success:
            return {"status": "success", "message": "Test message sent"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send message")
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-user/{chat_id}")
async def check_telegram_user(
    chat_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Diagnostic endpoint to check Telegram user configuration
    """
    try:
        chat_id_clean = chat_id.strip()
        
        # Check exact match
        result = await db.execute(
            select(UserPreferences).where(
                UserPreferences.telegram_chat_id == chat_id_clean
            )
        )
        user_prefs_exact = result.scalar_one_or_none()
        
        # Check with trim
        result_trim = await db.execute(
            select(UserPreferences).where(
                func.trim(UserPreferences.telegram_chat_id) == chat_id_clean
            )
        )
        user_prefs_trim = result_trim.scalar_one_or_none()
        
        # Check with telegram_enabled == True (exact)
        result_enabled_exact = await db.execute(
            select(UserPreferences).where(
                UserPreferences.telegram_chat_id == chat_id_clean,
                UserPreferences.telegram_enabled == True
            )
        )
        user_prefs_enabled_exact = result_enabled_exact.scalar_one_or_none()
        
        # Check with trim AND telegram_enabled == True
        result_enabled_trim = await db.execute(
            select(UserPreferences).where(
                func.trim(UserPreferences.telegram_chat_id) == chat_id_clean,
                UserPreferences.telegram_enabled == True
            )
        )
        user_prefs_enabled_trim = result_enabled_trim.scalar_one_or_none()
        
        # Get user email if found
        user_email = None
        if user_prefs_exact:
            user_result = await db.execute(
                select(User).where(User.id == user_prefs_exact.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                user_email = user.email
        
        return {
            "chat_id": chat_id_clean,
            "exact_match": {
                "found": user_prefs_exact is not None,
                "telegram_enabled": user_prefs_exact.telegram_enabled if user_prefs_exact else None,
                "telegram_chat_id": user_prefs_exact.telegram_chat_id if user_prefs_exact else None,
                "chat_id_repr": repr(user_prefs_exact.telegram_chat_id) if user_prefs_exact else None,
                "user_id": str(user_prefs_exact.user_id) if user_prefs_exact else None,
            },
            "trim_match": {
                "found": user_prefs_trim is not None,
                "telegram_enabled": user_prefs_trim.telegram_enabled if user_prefs_trim else None,
            },
            "exact_with_enabled": {
                "found": user_prefs_enabled_exact is not None,
            },
            "trim_with_enabled": {
                "found": user_prefs_enabled_trim is not None,
            },
            "user_email": user_email,
            "can_use_digest": user_prefs_enabled_exact is not None or user_prefs_enabled_trim is not None,
            "diagnosis": (
                "✅ User found and telegram_enabled == True. /digest should work!"
                if (user_prefs_enabled_exact or user_prefs_enabled_trim) else
                "⚠️ User found but telegram_enabled == False. Enable Telegram notifications in settings."
                if user_prefs_exact else
                "❌ User not found. Add Chat ID to profile settings."
            )
        }
        
    except Exception as e:
        logger.error(f"Error checking Telegram user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_help_callback(chat_id: str, db: AsyncSession):
    """Handle help callback query"""
    try:
        help_text = (
            "🤖 **AI Competitor Insight Hub - Help**\n\n"
            "**Available Commands:**\n"
            "• /start - Main menu\n"
            "• /help - Show this help\n"
            "• /digest - Get news digest\n"
            "• /subscribe - Subscribe to notifications\n"
            "• /unsubscribe - Unsubscribe from notifications\n"
            "• /settings - Profile settings\n\n"
            "**Menu Buttons:**\n"
            "• 📅 Daily Digest - news from the last 24 hours\n"
            "• 📊 Weekly Digest - news from the last 7 days\n"
            "• ⚙️ Settings - manage preferences\n"
            "• 🔗 Web App - go to website\n\n"
            "**Setup:**\n"
            "1. Copy your Chat ID from the main menu\n"
            "2. Open the web application\n"
            "3. Add Chat ID to profile settings\n"
            "4. Enable Telegram notifications\n"
            "5. Configure news categories and companies\n\n"
            "**Support:**\n"
            "If you have questions, please contact the administrator."
        )
        
        # Create keyboard to return to main menu
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🏠 Main Menu", "callback_data": "main_menu"}
                ]
            ]
        }
        
        await telegram_service.send_message_with_keyboard(chat_id, help_text, keyboard)
        
    except Exception as e:
        logger.error(f"Error handling help callback: {e}")
        await telegram_service.send_digest(
            chat_id,
            "❌ Error showing help. Please try again later."
        )


async def handle_main_menu_callback(chat_id: str, db: AsyncSession):
    """Handle main menu callback query - return to start menu"""
    try:
        from app.bot.handlers import handle_start
        
        # Get username from database if available
        from sqlalchemy import select
        
        # Expire all cached data to ensure we get fresh data from database
        db.expire_all()
        
        result = await db.execute(
            select(UserPreferences).where(
                UserPreferences.telegram_chat_id == chat_id,
                UserPreferences.telegram_enabled == True
            )
        )
        user_prefs = result.scalar_one_or_none()
        username = None  # We don't store username, but this is fine
        
        # Use the existing handle_start function to show main menu
        await handle_start(chat_id, username)
        
    except Exception as e:
        logger.error(f"Error handling main menu callback: {e}")
        await telegram_service.send_digest(
            chat_id,
            "❌ Error returning to main menu. Use /start"
        )
