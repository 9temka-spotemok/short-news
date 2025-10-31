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
        "👋 Welcome to AI Competitor Insight Hub!\n\n"
        f"Your Chat ID: `{chat_id}`\n\n"
        "Copy this ID and add it to your profile settings on the web platform "
        "to receive personalized news digests.\n\n"
        "Choose an action:"
    )
    
    # Create inline keyboard
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📅 Daily Digest", "callback_data": "digest_daily"},
                {"text": "📊 Weekly Digest", "callback_data": "digest_weekly"}
            ],
            [
                {"text": "⚙️ Digest Settings", "callback_data": "settings_digest"},
                {"text": "📚 Help", "callback_data": "help"}
            ],
            [
                {"text": "🔗 Open Web App", "url": "https://yourdomain.com"}
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
    """Handle /digest command: open Digest Settings menu immediately"""
    from app.core.database import AsyncSessionLocal
    from app.models import UserPreferences
    from sqlalchemy import select, func
    from loguru import logger

    try:
        chat_id_clean = chat_id.strip()

        async with AsyncSessionLocal() as db:
            # Find user by telegram_chat_id (using trim to handle any whitespace issues)
            # AND check that telegram_enabled is True
            result = await db.execute(
                select(UserPreferences).where(
                    func.trim(UserPreferences.telegram_chat_id) == chat_id_clean,
                    UserPreferences.telegram_enabled == True
                )
            )
            user_prefs = result.scalar_one_or_none()

            # If not found, try without trim (fallback)
            if not user_prefs:
                result = await db.execute(
                    select(UserPreferences).where(
                        UserPreferences.telegram_chat_id == chat_id_clean,
                        UserPreferences.telegram_enabled == True
                    )
                )
                user_prefs = result.scalar_one_or_none()

            if not user_prefs:
                # Log diagnostic info to help debug the issue
                result_debug = await db.execute(
                    select(UserPreferences).where(
                        func.trim(UserPreferences.telegram_chat_id) == chat_id_clean
                    )
                )
                user_prefs_debug = result_debug.scalar_one_or_none()
                
                # If still not found, try without trim
                if not user_prefs_debug:
                    result_debug = await db.execute(
                        select(UserPreferences).where(
                            UserPreferences.telegram_chat_id == chat_id_clean
                        )
                    )
                    user_prefs_debug = result_debug.scalar_one_or_none()
                
                logger.warning(
                    f"User not found for chat_id={chat_id_clean} in handle_digest. "
                    f"Found user without enabled check: {user_prefs_debug.user_id if user_prefs_debug else 'None'}. "
                    f"telegram_enabled={user_prefs_debug.telegram_enabled if user_prefs_debug else 'N/A'}"
                )
                
                error_text = (
                    "❌ User not found or Telegram not configured.\n\n"
                    "Make sure you:\n"
                    "1. Added Chat ID to your profile settings\n"
                    "2. Enabled Telegram notifications\n"
                    "3. Configured digests\n\n"
                    f"Your Chat ID: `{chat_id_clean}`"
                )
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "🔗 Open Settings", "url": "https://short-news-ai.netlify.app/digest-settings"}
                        ]
                    ]
                }
                await telegram_service.send_message_with_keyboard(chat_id, error_text, keyboard)
                return ""

            current_mode = user_prefs.telegram_digest_mode or 'all'
            await telegram_service.send_digest_settings_menu(chat_id_clean, current_mode)
            return ""

    except Exception as e:
        logger.error(f"Error in handle_digest: {e}")
        await telegram_service.send_digest(chat_id, "❌ Error. Please try again later.")
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



