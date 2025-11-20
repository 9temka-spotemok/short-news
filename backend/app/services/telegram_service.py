"""
Telegram bot service
"""

from typing import Dict, Any, Optional
from loguru import logger
import aiohttp
import asyncio
import time
from collections import deque
from app.core.config import settings


class TelegramRateLimiter:
    """
    Rate limiter for Telegram API calls.
    
    Telegram allows up to 20 messages per second per bot.
    This limiter ensures we don't exceed this limit.
    """
    
    def __init__(self, max_per_second: int = 20):
        """
        Initialize rate limiter.
        
        Args:
            max_per_second: Maximum number of requests per second (default: 20 for Telegram)
        """
        self._max_per_second = max_per_second
        self._request_times: deque = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self, chat_id: str) -> None:
        """
        Acquire permission to send a message.
        
        This will block if the rate limit is exceeded.
        
        Args:
            chat_id: Chat ID (for logging purposes, not used for per-chat limiting)
        """
        now = time.monotonic()
        
        async with self._lock:
            # Remove timestamps older than 1 second
            while self._request_times and now - self._request_times[0] >= 1.0:
                self._request_times.popleft()
            
            # If we've hit the limit, wait until we can send
            if len(self._request_times) >= self._max_per_second:
                # Calculate how long to wait
                oldest_time = self._request_times[0]
                wait_time = 1.0 - (now - oldest_time)
                if wait_time > 0:
                    logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s before sending to {chat_id}")
                    await asyncio.sleep(wait_time)
                    # Recalculate after wait
                    now = time.monotonic()
                    while self._request_times and now - self._request_times[0] >= 1.0:
                        self._request_times.popleft()
            
            # Record this request
            self._request_times.append(now)
    
    def release(self, chat_id: str) -> None:
        """
        Release permission (for compatibility with context manager pattern).
        
        Args:
            chat_id: Chat ID (not used, but kept for API consistency)
        """
        # No-op for now, as we're using time-based limiting
        pass


class TelegramService:
    """Service for Telegram bot interactions"""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN if hasattr(settings, 'TELEGRAM_BOT_TOKEN') else None
        self.channel_id = settings.TELEGRAM_CHANNEL_ID if hasattr(settings, 'TELEGRAM_CHANNEL_ID') else None
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        # Initialize rate limiter (20 messages per second as per Telegram API limits)
        self._rate_limiter = TelegramRateLimiter(max_per_second=20)
    
    async def send_digest(self, chat_id: str, digest_text: str) -> bool:
        """
        Send digest to a specific chat
        
        Args:
            chat_id: Telegram chat ID
            digest_text: Formatted digest text
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"send_digest called: chat_id={chat_id}, text_length={len(digest_text)}")
        
        if not self.bot_token:
            logger.warning(f"Telegram bot token not configured. Cannot send message to chat_id={chat_id}")
            return False
        
        if not self.base_url:
            logger.error(f"base_url not set. bot_token exists but base_url is None")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            logger.debug(f"Sending message to URL: {url[:50]}... (chat_id: {chat_id})")
            
            # Split message if too long (Telegram limit is 4096 characters)
            messages = self._split_message(digest_text)
            logger.debug(f"Split into {len(messages)} message(s)")
            
            for i, message in enumerate(messages):
                # Apply rate limiting before sending
                await self._rate_limiter.acquire(chat_id)
                
                payload = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
                }
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=payload) as response:
                            logger.debug(f"Response status: {response.status}, chat_id: {chat_id}, message_part: {i+1}/{len(messages)}")
                            
                            if response.status != 200:
                                response_text = await response.text()
                                logger.error(f"Failed to send Telegram message to chat_id={chat_id}: HTTP {response.status}, response: {response_text[:200]}")
                                return False
                            
                            try:
                                result = await response.json()
                            except Exception as json_error:
                                response_text = await response.text()
                                logger.error(f"Failed to parse JSON response: {json_error}, response text: {response_text[:200]}")
                                return False
                            
                            if not result.get("ok"):
                                error_desc = result.get("description", "Unknown error")
                                logger.error(f"Telegram API error for chat_id={chat_id}: {error_desc}, full response: {result}")
                                return False
                finally:
                    # Release rate limiter (for consistency, though it's a no-op)
                    self._rate_limiter.release(chat_id)
            
            logger.info(f"Digest sent successfully to chat {chat_id} ({len(messages)} message(s))")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Telegram message to chat_id={chat_id}: {e}", exc_info=True)
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
            return "❓ Unknown command. Use /help for available commands."
    
    def _handle_start_command(self, chat_id: str) -> str:
        """Handle /start command"""
        return (
            "👋 Welcome to AI Competitor Insight Hub!\n\n"
            f"Your Chat ID: `{chat_id}`\n\n"
            "Copy this ID and add it to your profile settings on the web platform "
            "to receive personalized news digests.\n\n"
            "Use /help for a list of available commands."
        )
    
    def _handle_help_command(self) -> str:
        """Handle /help command"""
        return (
            "📚 **Available commands:**\n\n"
            "/start - Start and get Chat ID\n"
            "/help - Show this help\n"
            "/subscribe - Subscribe to digests\n"
            "/unsubscribe - Unsubscribe from digests\n"
            "/settings - Show current settings\n"
            "/digest - Get latest digest\n\n"
            "Use the web application to configure personalized digests."
        )
    
    def _handle_subscribe_command(self, chat_id: str) -> str:
        """Handle /subscribe command"""
        return (
            "✅ You are subscribed to digests!\n\n"
            "To configure digest frequency and content, go to settings on the web platform.\n"
            f"Your Chat ID: `{chat_id}`"
        )
    
    def _handle_unsubscribe_command(self, chat_id: str) -> str:
        """Handle /unsubscribe command"""
        return (
            "❌ You are unsubscribed from digests.\n\n"
            "Use /subscribe to resubscribe."
        )
    
    def _handle_settings_command(self, chat_id: str) -> str:
        """Handle /settings command"""
        return (
            "⚙️ **Settings**\n\n"
            f"Chat ID: `{chat_id}`\n\n"
            "Use the web application to change digest and notification settings."
        )
    
    def _handle_digest_command(self, chat_id: str) -> str:
        """Handle /digest command"""
        return (
            "📰 Generating digest...\n\n"
            "Your personalized digest will be sent shortly!"
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
    
    async def send_digest_settings_menu(self, chat_id: str, current_mode: str) -> bool:
        """Send digest settings menu with inline keyboard"""
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": f"{'✅' if current_mode == 'all' else '❌'} All News",
                        "callback_data": "digest_settings_all"
                    },
                    {
                        "text": f"{'✅' if current_mode == 'tracked' else '❌'} Tracked Only",
                        "callback_data": "digest_settings_tracked"
                    }
                ],
                [
                    {"text": "🔙 Back to Main Menu", "callback_data": "main_menu"}
                ]
            ]
        }
        
        message = (
            "🛠️ **Digest Settings**\n\n"
            f"Current mode: **{'All News' if current_mode == 'all' else 'Tracked Only'}**\n\n"
            "Choose digest mode:\n"
            "• **All News** — all available news\n"
            "• **Tracked Only** — only news from your tracked companies"
        )
        
        return await self.send_message_with_keyboard(chat_id, message, keyboard)
    
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
                
                # Apply rate limiting before sending
                await self._rate_limiter.acquire(chat_id)
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=payload) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                logger.error(f"Failed to send Telegram message with keyboard: {response.status} - {error_text}")
                                return False
                            
                            result = await response.json()
                            if not result.get("ok"):
                                logger.error(f"Telegram API error: {result}")
                                return False
                finally:
                    # Release rate limiter (for consistency, though it's a no-op)
                    self._rate_limiter.release(chat_id)
            
            logger.info(f"Message with keyboard sent to chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Telegram message with keyboard: {e}")
            return False

    async def send_post_digest_controls(self, chat_id: str) -> bool:
        """
        Send quick action controls after a digest is delivered.
        Provides buttons to request another digest or open settings.
        """
        controls_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📅 Daily", "callback_data": "digest_daily"},
                    {"text": "📊 Weekly", "callback_data": "digest_weekly"}
                ],
                [
                    {"text": "⚙️ Settings", "callback_data": "settings_digest"},
                    {"text": "🏠 Main menu", "callback_data": "main_menu"}
                ]
            ]
        }
        message = (
            "What would you like to do next?\n\n"
            "Choose one of the options below."
        )
        return await self.send_message_with_keyboard(chat_id, message, controls_keyboard)


# Global instance
telegram_service = TelegramService()



