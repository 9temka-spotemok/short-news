"""
Telegram webhook endpoints
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger
import json
from datetime import datetime, timedelta

from app.core.database import get_db
from app.services.telegram_service import telegram_service
from app.bot.handlers import handle_message
from app.models import UserPreferences
from app.tasks.digest import generate_user_digest
from sqlalchemy import select

router = APIRouter()

# Simple in-memory cache for user preferences (expires after 5 minutes)
_user_prefs_cache = {}
_cache_expiry = {}

def _get_cached_user_prefs(chat_id: str) -> Optional[UserPreferences]:
    """Get cached user preferences if not expired"""
    if chat_id in _user_prefs_cache and chat_id in _cache_expiry:
        if datetime.utcnow() < _cache_expiry[chat_id]:
            return _user_prefs_cache[chat_id]
        else:
            # Remove expired cache
            del _user_prefs_cache[chat_id]
            del _cache_expiry[chat_id]
    return None

def _cache_user_prefs(chat_id: str, user_prefs: UserPreferences):
    """Cache user preferences for 5 minutes"""
    _user_prefs_cache[chat_id] = user_prefs
    _cache_expiry[chat_id] = datetime.utcnow().replace(microsecond=0) + timedelta(minutes=5)


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
        
        # If it's a /digest command, also trigger actual digest generation
        if text.startswith('/digest'):
            await handle_digest_command_real(chat_id, db)
            
    except Exception as e:
        logger.error(f"Error handling Telegram message: {e}")


async def handle_telegram_callback(callback_query: Dict[str, Any], db: AsyncSession):
    """Handle Telegram callback queries (inline keyboard buttons)"""
    try:
        chat_id = str(callback_query["message"]["chat"]["id"])
        data = callback_query.get("data", "")
        
        logger.info(f"Processing callback from {chat_id}: {data}")
        
        # Handle different callback types
        if data.startswith("digest_"):
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
        logger.error(f"Error handling Telegram callback: {e}")


async def handle_channel_post(channel_post: Dict[str, Any], db: AsyncSession):
    """Handle channel posts (for public channel)"""
    logger.info(f"Channel post received: {channel_post}")
    # Channel posts are usually from other admins, we don't need to respond


async def handle_digest_command_real(chat_id: str, db: AsyncSession):
    """Handle real /digest command - find user and trigger digest generation"""
    try:
        # Find user by telegram_chat_id
        result = await db.execute(
            select(UserPreferences).where(
                UserPreferences.telegram_chat_id == chat_id,
                UserPreferences.telegram_enabled == True
            )
        )
        user_prefs = result.scalar_one_or_none()
        
        if not user_prefs:
            # User not found or Telegram not enabled
            await telegram_service.send_digest(
                chat_id, 
                "❌ Пользователь не найден или Telegram не настроен.\n\n"
                "Убедитесь, что вы:\n"
                "1. Добавили Chat ID в настройки профиля\n"
                "2. Включили отправку в Telegram\n"
                "3. Настроили дайджесты"
            )
            return
        
        # Trigger digest generation
        task = generate_user_digest.delay(str(user_prefs.user_id), "daily")
        
        await telegram_service.send_digest(
            chat_id,
            "📰 Дайджест генерируется...\n\n"
            "Ваш персонализированный дайджест будет отправлен в ближайшее время!"
        )
        
        logger.info(f"Digest generation triggered for user {user_prefs.user_id}")
        
    except Exception as e:
        logger.error(f"Error handling real digest command: {e}")
        await telegram_service.send_digest(
            chat_id,
            "❌ Ошибка при генерации дайджеста. Попробуйте позже."
        )


async def handle_digest_callback(chat_id: str, data: str, db: AsyncSession):
    """Handle digest-related callback queries"""
    from app.tasks.digest import generate_user_digest
    from sqlalchemy import select
    
    try:
        # Try to get cached user preferences first
        user_prefs = _get_cached_user_prefs(chat_id)
        
        if not user_prefs:
            # Find user by telegram_chat_id and cache the result
            result = await db.execute(
                select(UserPreferences).where(
                    UserPreferences.telegram_chat_id == chat_id,
                    UserPreferences.telegram_enabled == True
                )
            )
            user_prefs = result.scalar_one_or_none()
            
            if user_prefs:
                _cache_user_prefs(chat_id, user_prefs)
        
        if not user_prefs:
            await telegram_service.send_digest(
                chat_id,
                "❌ Пользователь не найден. Настройте Telegram в веб-приложении."
            )
            return
        
        if data == "digest_daily":
            task = generate_user_digest.delay(str(user_prefs.user_id), "daily")
            await telegram_service.send_digest(
                chat_id,
                "📅 Дневной дайджест генерируется...\n\n"
                "Ваш персонализированный дайджест будет отправлен в ближайшее время!"
            )
        elif data == "digest_weekly":
            task = generate_user_digest.delay(str(user_prefs.user_id), "weekly")
            await telegram_service.send_digest(
                chat_id,
                "📊 Недельный дайджест генерируется...\n\n"
                "Ваш персонализированный дайджест будет отправлен в ближайшее время!"
            )
        elif data == "settings_digest":
            await handle_digest_settings_callback(chat_id, db)
            
    except Exception as e:
        logger.error(f"Error handling digest callback: {e}")
        await telegram_service.send_digest(
            chat_id,
            "❌ Ошибка при генерации дайджеста. Попробуйте позже."
        )


async def handle_digest_settings_callback(chat_id: str, db: AsyncSession):
    """Handle digest settings callback"""
    try:
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.telegram_chat_id == chat_id)
        )
        user_prefs = result.scalar_one_or_none()
        
        if user_prefs:
            settings_text = f"""
⚙️ **Настройки дайджеста:**

📊 Дайджесты: {'✅ Включены' if user_prefs.digest_enabled else '❌ Отключены'}
📅 Частота: {user_prefs.digest_frequency.value if user_prefs.digest_frequency else 'Не настроено'}
📝 Формат: {user_prefs.digest_format.value if user_prefs.digest_format else 'Не настроено'}
🌐 Часовой пояс: {user_prefs.timezone if hasattr(user_prefs, 'timezone') else 'UTC'}

Для изменения настроек используйте веб-приложение.
            """
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🔗 Открыть настройки", "url": "https://yourdomain.com/settings/digest"}
                    ]
                ]
            }
            
            await telegram_service.send_message_with_keyboard(chat_id, settings_text, keyboard)
        
    except Exception as e:
        logger.error(f"Error handling digest settings callback: {e}")
        await telegram_service.send_digest(
            chat_id,
            "❌ Ошибка при получении настроек. Попробуйте позже."
        )


async def handle_settings_callback(chat_id: str, data: str, db: AsyncSession):
    """Handle settings-related callback queries"""
    if data == "settings_view":
        # Show current settings
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.telegram_chat_id == chat_id)
        )
        user_prefs = result.scalar_one_or_none()
        
        if user_prefs:
            settings_text = f"""
⚙️ **Ваши настройки:**

📊 Дайджесты: {'✅ Включены' if user_prefs.digest_enabled else '❌ Отключены'}
📅 Частота: {user_prefs.digest_frequency.value if user_prefs.digest_frequency else 'Не настроено'}
📝 Формат: {user_prefs.digest_format.value if user_prefs.digest_format else 'Не настроено'}
🌐 Часовой пояс: {user_prefs.timezone if hasattr(user_prefs, 'timezone') else 'UTC'}

Для изменения настроек используйте веб-приложение.
            """
            await telegram_service.send_digest(chat_id, settings_text)


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
    message: str = "🧪 Тестовое сообщение от AI Competitor Insight Hub"
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


async def handle_help_callback(chat_id: str, db: AsyncSession):
    """Handle help callback query"""
    try:
        help_text = (
            "🤖 **AI Competitor Insight Hub - Помощь**\n\n"
            "**Доступные команды:**\n"
            "• /start - Главное меню\n"
            "• /help - Показать эту справку\n"
            "• /digest - Получить дайджест новостей\n"
            "• /subscribe - Подписаться на уведомления\n"
            "• /unsubscribe - Отписаться от уведомлений\n"
            "• /settings - Настройки профиля\n\n"
            "**Кнопки в меню:**\n"
            "• 📅 Дневной дайджест - новости за последние 24 часа\n"
            "• 📊 Недельный дайджест - новости за последние 7 дней\n"
            "• ⚙️ Настройки - управление предпочтениями\n"
            "• 🔗 Веб-приложение - переход на сайт\n\n"
            "**Настройка:**\n"
            "1. Скопируйте ваш Chat ID из главного меню\n"
            "2. Откройте веб-приложение\n"
            "3. Добавьте Chat ID в настройки профиля\n"
            "4. Включите отправку в Telegram\n"
            "5. Настройте категории новостей и компании\n\n"
            "**Поддержка:**\n"
            "Если у вас есть вопросы, обратитесь к администратору."
        )
        
        # Create keyboard to return to main menu
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🏠 Главное меню", "callback_data": "main_menu"}
                ]
            ]
        }
        
        await telegram_service.send_message_with_keyboard(chat_id, help_text, keyboard)
        
    except Exception as e:
        logger.error(f"Error handling help callback: {e}")
        await telegram_service.send_digest(
            chat_id,
            "❌ Ошибка при показе справки. Попробуйте позже."
        )


async def handle_main_menu_callback(chat_id: str, db: AsyncSession):
    """Handle main menu callback query - return to start menu"""
    try:
        from app.bot.handlers import handle_start
        
        # Get username from database if available
        from sqlalchemy import select
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.telegram_chat_id == chat_id)
        )
        user_prefs = result.scalar_one_or_none()
        username = None  # We don't store username, but this is fine
        
        # Use the existing handle_start function to show main menu
        await handle_start(chat_id, username)
        
    except Exception as e:
        logger.error(f"Error handling main menu callback: {e}")
        await telegram_service.send_digest(
            chat_id,
            "❌ Ошибка при возврате в главное меню. Используйте /start"
        )
