"""
Telegram bot service
"""

from typing import Dict, Any, Optional
from loguru import logger
import aiohttp
from app.core.config import settings


class TelegramService:
    """Service for Telegram bot interactions"""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN if hasattr(settings, 'TELEGRAM_BOT_TOKEN') else None
        self.channel_id = settings.TELEGRAM_CHANNEL_ID if hasattr(settings, 'TELEGRAM_CHANNEL_ID') else None
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
    
    async def send_digest(self, chat_id: str, digest_text: str) -> bool:
        """
        Send digest to a specific chat
        
        Args:
            chat_id: Telegram chat ID
            digest_text: Formatted digest text
            
        Returns:
            True if successful, False otherwise
        """
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            
            # Split message if too long (Telegram limit is 4096 characters)
            messages = self._split_message(digest_text)
            
            for message in messages:
                payload = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload) as response:
                        if response.status != 200:
                            logger.error(f"Failed to send Telegram message: {response.status}")
                            return False
                        
                        result = await response.json()
                        if not result.get("ok"):
                            logger.error(f"Telegram API error: {result}")
                            return False
            
            logger.info(f"Digest sent to chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    async def send_to_channel(self, digest_text: str) -> bool:
        """
        Send digest to the public channel
        
        Args:
            digest_text: Formatted digest text
            
        Returns:
            True if successful, False otherwise
        """
        if not self.channel_id:
            logger.warning("Telegram channel ID not configured")
            return False
        
        return await self.send_digest(self.channel_id, digest_text)
    
    async def send_notification(self, chat_id: str, title: str, message: str) -> bool:
        """
        Send a notification message
        
        Args:
            chat_id: Telegram chat ID
            title: Notification title
            message: Notification message
            
        Returns:
            True if successful, False otherwise
        """
        notification_text = f"🔔 **{title}**\n\n{message}"
        return await self.send_digest(chat_id, notification_text)
    
    def _split_message(self, text: str, max_length: int = 4000) -> list[str]:
        """
        Split message into chunks if it's too long
        
        Args:
            text: Message text
            max_length: Maximum length per message
            
        Returns:
            List of message chunks
        """
        if len(text) <= max_length:
            return [text]
        
        messages = []
        lines = text.split('\n')
        current_message = ""
        
        for line in lines:
            if len(current_message) + len(line) + 1 <= max_length:
                current_message += line + "\n"
            else:
                if current_message:
                    messages.append(current_message.strip())
                current_message = line + "\n"
        
        if current_message:
            messages.append(current_message.strip())
        
        return messages
    
    async def register_user(self, telegram_user_id: int, telegram_username: Optional[str] = None) -> str:
        """
        Generate registration link for user
        
        Args:
            telegram_user_id: Telegram user ID
            telegram_username: Telegram username
            
        Returns:
            Chat ID as string
        """
        return str(telegram_user_id)
    
    async def handle_command(self, command: str, chat_id: str, args: list[str] = None) -> str:
        """
        Handle bot commands
        
        Args:
            command: Command name (without /)
            chat_id: Chat ID
            args: Command arguments
            
        Returns:
            Response message
        """
        if command == "start":
            return self._handle_start_command(chat_id)
        elif command == "help":
            return self._handle_help_command()
        elif command == "subscribe":
            return self._handle_subscribe_command(chat_id)
        elif command == "unsubscribe":
            return self._handle_unsubscribe_command(chat_id)
        elif command == "settings":
            return self._handle_settings_command(chat_id)
        elif command == "digest":
            return self._handle_digest_command(chat_id)
        else:
            return "❓ Неизвестная команда. Используйте /help для списка команд."
    
    def _handle_start_command(self, chat_id: str) -> str:
        """Handle /start command"""
        return (
            "👋 Добро пожаловать в AI Competitor Insight Hub!\n\n"
            f"Ваш Chat ID: `{chat_id}`\n\n"
            "Скопируйте этот ID и добавьте его в настройки вашего профиля на веб-платформе, "
            "чтобы получать персонализированные дайджесты новостей.\n\n"
            "Используйте /help для списка доступных команд."
        )
    
    def _handle_help_command(self) -> str:
        """Handle /help command"""
        return (
            "📚 **Доступные команды:**\n\n"
            "/start - Начать работу и получить Chat ID\n"
            "/help - Показать эту справку\n"
            "/subscribe - Подписаться на дайджесты\n"
            "/unsubscribe - Отписаться от дайджестов\n"
            "/settings - Показать текущие настройки\n"
            "/digest - Получить последний дайджест\n\n"
            "Для настройки персонализированных дайджестов используйте веб-приложение."
        )
    
    def _handle_subscribe_command(self, chat_id: str) -> str:
        """Handle /subscribe command"""
        return (
            "✅ Вы подписаны на дайджесты!\n\n"
            "Для настройки частоты и содержания дайджестов перейдите в настройки на веб-платформе.\n"
            f"Ваш Chat ID: `{chat_id}`"
        )
    
    def _handle_unsubscribe_command(self, chat_id: str) -> str:
        """Handle /unsubscribe command"""
        return (
            "❌ Вы отписаны от дайджестов.\n\n"
            "Используйте /subscribe для повторной подписки."
        )
    
    def _handle_settings_command(self, chat_id: str) -> str:
        """Handle /settings command"""
        return (
            "⚙️ **Настройки**\n\n"
            f"Chat ID: `{chat_id}`\n\n"
            "Для изменения настроек дайджестов и уведомлений используйте веб-приложение."
        )
    
    def _handle_digest_command(self, chat_id: str) -> str:
        """Handle /digest command"""
        return (
            "📰 Генерация дайджеста...\n\n"
            "Дайджест будет отправлен в ближайшее время."
        )


# Global instance
telegram_service = TelegramService()

