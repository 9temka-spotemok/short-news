"""
Telegram bot handlers
"""

from typing import Optional
from loguru import logger

from app.services.telegram_service import telegram_service


async def handle_start(chat_id: str, username: Optional[str] = None) -> str:
    """Handle /start command"""
    from app.services.telegram_service import telegram_service
    
    # Create welcome message with inline keyboard
    welcome_text = (
        "👋 Добро пожаловать в AI Competitor Insight Hub!\n\n"
        f"Ваш Chat ID: `{chat_id}`\n\n"
        "Скопируйте этот ID и добавьте его в настройки вашего профиля на веб-платформе, "
        "чтобы получать персонализированные дайджесты новостей.\n\n"
        "Выберите действие:"
    )
    
    # Create inline keyboard
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📅 Дневной дайджест", "callback_data": "digest_daily"},
                {"text": "📊 Недельный дайджест", "callback_data": "digest_weekly"}
            ],
            [
                {"text": "⚙️ Настройки", "callback_data": "settings_view"},
                {"text": "📚 Помощь", "callback_data": "help"}
            ],
            [
                {"text": "🔗 Открыть веб-приложение", "url": "https://yourdomain.com"}
            ]
        ]
    }
    
    # Send message with keyboard
    await telegram_service.send_message_with_keyboard(chat_id, welcome_text, keyboard)
    return ""


async def handle_help(chat_id: str) -> str:
    """Handle /help command"""
    response = telegram_service._handle_help_command()
    return response


async def handle_subscribe(chat_id: str) -> str:
    """Handle /subscribe command"""
    response = telegram_service._handle_subscribe_command(chat_id)
    return response


async def handle_unsubscribe(chat_id: str) -> str:
    """Handle /unsubscribe command"""
    response = telegram_service._handle_unsubscribe_command(chat_id)
    return response


async def handle_settings(chat_id: str) -> str:
    """Handle /settings command"""
    response = telegram_service._handle_settings_command(chat_id)
    return response


async def handle_digest(chat_id: str) -> str:
    """Handle /digest command"""
    from app.core.database import AsyncSessionLocal
    from app.models import UserPreferences
    from app.tasks.digest import generate_user_digest
    from sqlalchemy import select
    
    try:
        async with AsyncSessionLocal() as db:
            # Find user by telegram_chat_id
            result = await db.execute(
                select(UserPreferences).where(
                    UserPreferences.telegram_chat_id == chat_id,
                    UserPreferences.telegram_enabled == True
                )
            )
            user_prefs = result.scalar_one_or_none()
            
            if not user_prefs:
                error_text = (
                    "❌ Пользователь не найден или Telegram не настроен.\n\n"
                    "Убедитесь, что вы:\n"
                    "1. Добавили Chat ID в настройки профиля\n"
                    "2. Включили отправку в Telegram\n"
                    "3. Настроили дайджесты\n\n"
                    f"Ваш Chat ID: `{chat_id}`"
                )
                
                # Send error message with setup keyboard
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "🔗 Открыть настройки", "url": "https://yourdomain.com/settings"}
                        ]
                    ]
                }
                await telegram_service.send_message_with_keyboard(chat_id, error_text, keyboard)
                return ""
            
            # Create digest selection keyboard
            digest_text = "📰 Выберите тип дайджеста:"
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "📅 Дневной дайджест", "callback_data": "digest_daily"},
                        {"text": "📊 Недельный дайджест", "callback_data": "digest_weekly"}
                    ],
                    [
                        {"text": "⚙️ Настройки дайджеста", "callback_data": "settings_digest"}
                    ]
                ]
            }
            
            await telegram_service.send_message_with_keyboard(chat_id, digest_text, keyboard)
            return ""
            
    except Exception as e:
        logger.error(f"Error in handle_digest: {e}")
        error_text = "❌ Ошибка при генерации дайджеста. Попробуйте позже."
        await telegram_service.send_digest(chat_id, error_text)
        return ""


async def handle_message(chat_id: str, text: str, username: Optional[str] = None) -> str:
    """
    Handle incoming message
    
    Args:
        chat_id: Telegram chat ID
        text: Message text
        username: Telegram username
        
    Returns:
        Response message
    """
    logger.info(f"Received message from {chat_id} ({username}): {text}")
    
    # Check if it's a command
    if text.startswith('/'):
        parts = text.split()
        command = parts[0][1:]  # Remove '/' prefix
        args = parts[1:] if len(parts) > 1 else []
        
        # Route command
        if command == 'start':
            return await handle_start(chat_id, username)
        elif command == 'help':
            return await handle_help(chat_id)
        elif command == 'subscribe':
            return await handle_subscribe(chat_id)
        elif command == 'unsubscribe':
            return await handle_unsubscribe(chat_id)
        elif command == 'settings':
            return await handle_settings(chat_id)
        elif command == 'digest':
            return await handle_digest(chat_id)
        else:
            return "❓ Unknown command. Use /help for available commands."
    
    # Not a command - friendly response
    return (
        "👋 Hi! I'm the AI Competitor Insight Hub bot.\n\n"
        "Use /help to see available commands."
    )



