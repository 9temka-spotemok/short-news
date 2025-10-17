#!/usr/bin/env python3
"""
Telegram bot polling script for development
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.telegram_service import telegram_service
from app.core.config import settings
from app.bot.handlers import handle_message
from app.core.database import AsyncSessionLocal
from loguru import logger
import aiohttp
import json

class TelegramPolling:
    """Telegram bot polling service"""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.offset = 0
        self.running = False
    
    async def get_updates(self):
        """Get updates from Telegram"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                "offset": self.offset,
                "timeout": 30,
                "allowed_updates": ["message", "callback_query"]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            return result.get("result", [])
                        else:
                            logger.error(f"Telegram API error: {result}")
                            return []
                    else:
                        logger.error(f"HTTP error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []
    
    async def process_update(self, update):
        """Process a single update"""
        try:
            update_id = update.get("update_id")
            self.offset = update_id + 1
            
            # Handle message
            if "message" in update:
                await self.handle_message(update["message"])
            
            # Handle callback query
            elif "callback_query" in update:
                await self.handle_callback_query(update["callback_query"])
                
        except Exception as e:
            logger.error(f"Error processing update: {e}")
    
    async def handle_message(self, message):
        """Handle incoming message"""
        try:
            chat = message.get("chat", {})
            chat_id = str(chat.get("id"))
            text = message.get("text", "")
            user = message.get("from", {})
            username = user.get("username")
            
            logger.info(f"Received message from {chat_id} ({username}): {text}")
            
            # Process message through handlers
            try:
                async with AsyncSessionLocal() as db:
                    response = await handle_message(chat_id, text, username)
                    if response:
                        await telegram_service.send_digest(chat_id, response)
            except Exception as db_error:
                logger.error(f"Database error handling message: {db_error}")
                await telegram_service.send_digest(chat_id, "❌ Ошибка подключения к базе данных. Попробуйте позже.")
                    
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def handle_callback_query(self, callback_query):
        """Handle callback query from inline keyboard"""
        try:
            chat = callback_query.get("message", {}).get("chat", {})
            chat_id = str(chat.get("id"))
            data = callback_query.get("data", "")
            query_id = callback_query.get("id")
            
            logger.info(f"Received callback query from {chat_id}: {data}")
            
            # Answer callback query to remove loading state
            await telegram_service.answer_callback_query(query_id)
            
            # Process callback through handlers
            try:
                async with AsyncSessionLocal() as db:
                    if data == "digest_daily":
                        await self.handle_digest_callback(chat_id, "daily", db)
                    elif data == "digest_weekly":
                        await self.handle_digest_callback(chat_id, "weekly", db)
                    elif data == "settings_view":
                        await self.handle_settings_callback(chat_id, db)
                    elif data == "settings_digest":
                        await self.handle_digest_settings_callback(chat_id, db)
                    elif data == "help":
                        await self.handle_help_callback(chat_id, db)
                    elif data == "main_menu":
                        await self.handle_main_menu_callback(chat_id, db)
            except Exception as db_error:
                logger.error(f"Database error handling callback: {db_error}")
                await telegram_service.send_digest(chat_id, "❌ Ошибка подключения к базе данных. Попробуйте позже.")
                    
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
    
    async def handle_digest_callback(self, chat_id: str, digest_type: str, db):
        """Handle digest callback"""
        try:
            from app.models import UserPreferences
            from app.tasks.digest import generate_user_digest
            from sqlalchemy import select
            
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
                await telegram_service.send_digest(chat_id, error_text)
                return
            
            # Send processing message
            await telegram_service.send_digest(chat_id, "🔄 Генерирую дайджест...")
            
            # Generate digest using Celery task
            task = generate_user_digest.delay(str(user_prefs.user_id), digest_type)
            logger.info(f"Digest generation task started: {task.id} for user {user_prefs.user_id}")
            
            # Send completion message
            await telegram_service.send_digest(chat_id, "✅ Дайджест генерируется в фоне и будет отправлен в ближайшее время!")
            
        except Exception as e:
            logger.error(f"Error handling digest callback: {e}")
            await telegram_service.send_digest(chat_id, "❌ Ошибка при генерации дайджеста")
    
    async def handle_settings_callback(self, chat_id: str, db):
        """Handle settings callback"""
        try:
            from app.models import UserPreferences
            from sqlalchemy import select
            
            result = await db.execute(
                select(UserPreferences).where(UserPreferences.telegram_chat_id == chat_id)
            )
            user_prefs = result.scalar_one_or_none()
            
            if user_prefs:
                settings_text = (
                    f"⚙️ **Настройки**\n\n"
                    f"Chat ID: `{chat_id}`\n"
                    f"Дайджесты: {'✅' if user_prefs.digest_enabled else '❌'}\n"
                    f"Частота: {user_prefs.digest_frequency or 'Не настроено'}\n"
                    f"Формат: {user_prefs.digest_format or 'Не настроено'}\n\n"
                    "Для изменения настроек используйте веб-приложение."
                )
            else:
                settings_text = (
                    "⚙️ **Настройки**\n\n"
                    f"Chat ID: `{chat_id}`\n\n"
                    "Пользователь не найден. Настройте профиль в веб-приложении."
                )
            
            await telegram_service.send_digest(chat_id, settings_text)
            
        except Exception as e:
            logger.error(f"Error handling settings callback: {e}")
    
    async def handle_help_callback(self, chat_id: str, db):
        """Handle help callback"""
        try:
            help_text = (
                "📚 **Доступные команды:**\n\n"
                "/start - Начать работу и получить Chat ID\n"
                "/help - Показать эту справку\n"
                "/digest - Получить дайджест\n"
                "/settings - Показать настройки\n\n"
                "**Интерактивные кнопки:**\n"
                "📅 Дневной дайджест - Получить дайджест за день\n"
                "📊 Недельный дайджест - Получить дайджест за неделю\n"
                "⚙️ Настройки - Показать текущие настройки\n\n"
                "Для настройки персонализированных дайджестов используйте веб-приложение."
            )
            
            await telegram_service.send_digest(chat_id, help_text)
            
        except Exception as e:
            logger.error(f"Error handling help callback: {e}")
    
    async def handle_digest_settings_callback(self, chat_id: str, db):
        """Handle digest settings callback"""
        try:
            from app.models import UserPreferences
            from app.core.config import settings
            from sqlalchemy import select
            
            result = await db.execute(
                select(UserPreferences).where(UserPreferences.telegram_chat_id == chat_id)
            )
            user_prefs = result.scalar_one_or_none()
            
            if user_prefs:
                # Safe access to enum values
                frequency = user_prefs.digest_frequency.value if user_prefs.digest_frequency else 'Не настроено'
                format_type = user_prefs.digest_format.value if user_prefs.digest_format else 'Не настроено'
                timezone = getattr(user_prefs, 'timezone', 'UTC')
                
                settings_text = f"""
⚙️ **Настройки дайджеста:**

📊 Дайджесты: {'✅ Включены' if user_prefs.digest_enabled else '❌ Отключены'}
📅 Частота: {frequency}
📝 Формат: {format_type}
🌐 Часовой пояс: {timezone}

Для изменения настроек используйте веб-приложение.
                """
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "🔗 Открыть настройки", "url": settings.FRONTEND_DIGEST_SETTINGS_URL}
                        ]
                    ]
                }
                
                await telegram_service.send_message_with_keyboard(chat_id, settings_text, keyboard)
            else:
                await telegram_service.send_digest(chat_id, "❌ Пользователь не найден. Настройте профиль в веб-приложении.")
            
        except Exception as e:
            logger.error(f"Error handling digest settings callback: {e}")
            await telegram_service.send_digest(chat_id, "❌ Ошибка при получении настроек. Попробуйте позже.")
    
    async def handle_main_menu_callback(self, chat_id: str, db):
        """Handle main menu callback - return to start menu"""
        try:
            from app.bot.handlers import handle_start
            
            # Use the existing handle_start function to show main menu
            await handle_start(chat_id, None)
            
        except Exception as e:
            logger.error(f"Error handling main menu callback: {e}")
            await telegram_service.send_digest(chat_id, "❌ Ошибка при возврате в главное меню. Используйте /start")
    
    async def start_polling(self):
        """Start polling for updates"""
        if not self.bot_token:
            logger.error("Telegram bot token not configured!")
            return
        
        logger.info("🤖 Starting Telegram bot polling...")
        self.running = True
        
        try:
            while self.running:
                updates = await self.get_updates()
                
                for update in updates:
                    await self.process_update(update)
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("🛑 Polling stopped by user")
        except Exception as e:
            logger.error(f"Polling error: {e}")
        finally:
            self.running = False
    
    def stop_polling(self):
        """Stop polling"""
        self.running = False

async def main():
    """Main function"""
    print("🤖 Starting Telegram Bot Polling")
    print("=" * 50)
    
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not configured!")
        print("Please run setup_telegram_bot_interactive.py first")
        return
    
    print(f"✅ Bot token configured: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
    print("🔄 Starting polling...")
    print("Press Ctrl+C to stop")
    
    polling = TelegramPolling()
    await polling.start_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Polling stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
