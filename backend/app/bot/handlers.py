"""
Telegram bot handlers
"""

from typing import Optional
from loguru import logger

from app.services.telegram_service import telegram_service


async def handle_start(chat_id: str, username: Optional[str] = None) -> str:
    """Handle /start command"""
    response = telegram_service._handle_start_command(chat_id)
    return response


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
    # Trigger digest generation
    from app.tasks.digest import generate_user_digest
    
    # Find user by chat_id and trigger digest
    # This is a simplified version - in real implementation,
    # we'd need to look up user by telegram_chat_id
    
    response = telegram_service._handle_digest_command(chat_id)
    return response


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



