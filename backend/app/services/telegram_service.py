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
            # If adding this line would exceed the limit
            if len(current_message) + len(line) + 1 > max_length:
                # If current message has content, save it
                if current_message.strip():
                    messages.append(current_message.strip())
                    current_message = ""
                
                # If single line is too long, split it
                if len(line) > max_length:
                    # Split long line by words
                    words = line.split(' ')
                    temp_line = ""
                    for word in words:
                        if len(temp_line) + len(word) + 1 > max_length:
                            if temp_line:
                                messages.append(temp_line.strip())
                                temp_line = word
                            else:
                                # Single word is too long, truncate it
                                messages.append(word[:max_length-3] + "...")
                                temp_line = ""
                        else:
                            temp_line += (" " + word) if temp_line else word
                    current_message = temp_line
                else:
                    current_message = line
            else:
                current_message += line + "\n"
        
        if current_message.strip():
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
            "Ваш персонализированный дайджест будет отправлен в ближайшее время!"
        )
    
    async def set_webhook(self, webhook_url: str) -> bool:
        """
        Set Telegram webhook URL
        
        Args:
            webhook_url: Webhook URL to set
            
        Returns:
            True if successful, False otherwise
        """
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return False
        
        try:
            url = f"{self.base_url}/setWebhook"
            payload = {
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query", "channel_post"]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Failed to set webhook: {response.status}")
                        return False
                    
                    result = await response.json()
                    if not result.get("ok"):
                        logger.error(f"Telegram API error setting webhook: {result}")
                        return False
            
            logger.info(f"Webhook set successfully: {webhook_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False
    
    async def delete_webhook(self) -> bool:
        """
        Delete Telegram webhook
        
        Returns:
            True if successful, False otherwise
        """
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return False
        
        try:
            url = f"{self.base_url}/deleteWebhook"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to delete webhook: {response.status}")
                        return False
                    
                    result = await response.json()
                    if not result.get("ok"):
                        logger.error(f"Telegram API error deleting webhook: {result}")
                        return False
            
            logger.info("Webhook deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return False
    
    async def get_webhook_info(self) -> dict:
        """
        Get current webhook information
        
        Returns:
            Webhook info dict
        """
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return {}
        
        try:
            url = f"{self.base_url}/getWebhookInfo"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get webhook info: {response.status}")
                        return {}
                    
                    result = await response.json()
                    if not result.get("ok"):
                        logger.error(f"Telegram API error getting webhook info: {result}")
                        return {}
                    
                    return result.get("result", {})
                    
        except Exception as e:
            logger.error(f"Error getting webhook info: {e}")
            return {}
    
    async def answer_callback_query(self, callback_query_id: str, text: str = None, show_alert: bool = False) -> bool:
        """
        Answer callback query to remove loading state
        
        Args:
            callback_query_id: Callback query ID
            text: Optional response text
            show_alert: Whether to show alert popup
            
        Returns:
            True if successful, False otherwise
        """
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return False
        
        try:
            url = f"{self.base_url}/answerCallbackQuery"
            payload = {
                "callback_query_id": callback_query_id
            }
            
            if text:
                payload["text"] = text
            if show_alert:
                payload["show_alert"] = show_alert
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Failed to answer callback query: {response.status}")
                        return False
                    
                    result = await response.json()
                    if not result.get("ok"):
                        logger.error(f"Telegram API error answering callback query: {result}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")
            return False
    
    async def send_message_with_keyboard(self, chat_id: str, text: str, keyboard: dict = None) -> bool:
        """
        Send message with inline keyboard
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            keyboard: Inline keyboard markup
            
        Returns:
            True if successful, False otherwise
        """
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            
            # Split message if too long
            messages = self._split_message(text)
            
            for i, message in enumerate(messages):
                payload = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
                }
                
                # Add keyboard only to the last message
                if keyboard and i == len(messages) - 1:
                    payload["reply_markup"] = keyboard
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload) as response:
                        if response.status != 200:
                            logger.error(f"Failed to send Telegram message with keyboard: {response.status}")
                            return False
                        
                        result = await response.json()
                        if not result.get("ok"):
                            logger.error(f"Telegram API error: {result}")
                            return False
            
            logger.info(f"Message with keyboard sent to chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Telegram message with keyboard: {e}")
            return False


# Global instance
telegram_service = TelegramService()



