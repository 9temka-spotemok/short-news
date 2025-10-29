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
                await telegram_service.send_digest(chat_id, "❌ Database connection error. Please try again later.")
                    
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
                    elif data == "digest_settings_all":
                        await self.handle_digest_mode_change(chat_id, "all", db)
                    elif data == "digest_settings_tracked":
                        await self.handle_digest_mode_change(chat_id, "tracked", db)
                    elif data == "help":
                        await self.handle_help_callback(chat_id, db)
                    elif data == "settings_menu":
                        await self.handle_digest_settings_callback(chat_id, db)
                    elif data == "main_menu":
                        await self.handle_main_menu_callback(chat_id, db)
            except Exception as db_error:
                logger.error(f"Database error handling callback: {db_error}")
                await telegram_service.send_digest(chat_id, "❌ Database connection error. Please try again later.")
                    
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
    
    async def handle_digest_callback(self, chat_id: str, digest_type: str, db):
        """Handle digest callback"""
        try:
            from app.models import UserPreferences
            from app.services.digest_service import DigestService
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
                    "❌ User not found or Telegram not configured.\n\n"
                    "Make sure you:\n"
                    "1. Added Chat ID to your profile settings\n"
                    "2. Enabled Telegram notifications\n"
                    "3. Configured digests\n\n"
                    f"Your Chat ID: `{chat_id}`"
                )
                await telegram_service.send_digest(chat_id, error_text)
                return
            
            # Send processing message
            await telegram_service.send_digest(chat_id, "🔄 Generating digest...")
            
            # Determine tracked_only based on telegram_digest_mode
            tracked_only = (user_prefs.telegram_digest_mode == 'tracked') if user_prefs.telegram_digest_mode else False
            
            # Generate digest directly (without Celery)
            logger.info(f"Generating digest for user {user_prefs.user_id} (type: {digest_type}, tracked_only: {tracked_only})")
            
            digest_service = DigestService(db)
            digest_data = await digest_service.generate_user_digest(
                user_id=str(user_prefs.user_id),
                period=digest_type,
                format_type=user_prefs.digest_format or "short",
                tracked_only=tracked_only
            )
            
            # Format and send digest
            digest_text = digest_service.format_digest_for_telegram(digest_data, user_prefs)
            await telegram_service.send_digest(chat_id, digest_text)
            logger.info(f"Digest sent to chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error handling digest callback: {e}")
            await telegram_service.send_digest(chat_id, f"❌ Error generating digest: {str(e)}")
    
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
                    f"⚙️ **Settings**\n\n"
                    f"Chat ID: `{chat_id}`\n"
                    f"Digests: {'✅' if user_prefs.digest_enabled else '❌'}\n"
                    f"Frequency: {user_prefs.digest_frequency or 'Not configured'}\n"
                    f"Format: {user_prefs.digest_format or 'Not configured'}\n\n"
                    "Use the web application to change settings."
                )
            else:
                settings_text = (
                    "⚙️ **Settings**\n\n"
                    f"Chat ID: `{chat_id}`\n\n"
                    "User not found. Configure your profile in the web application."
                )
            
            await telegram_service.send_digest(chat_id, settings_text)
            
        except Exception as e:
            logger.error(f"Error handling settings callback: {e}")
    
    async def handle_help_callback(self, chat_id: str, db):
        """Handle help callback"""
        try:
            help_text = (
                "📚 **Available commands:**\n\n"
                "/start - Start and get Chat ID\n"
                "/help - Show this help\n"
                "/digest - Get digest\n"
                "/settings - Show settings\n\n"
                "**Interactive buttons:**\n"
                "📅 Daily digest - Get daily digest\n"
                "📊 Weekly digest - Get weekly digest\n"
                "⚙️ Settings - Show current settings\n\n"
                "Use the web application to configure personalized digests."
            )
            
            await telegram_service.send_digest(chat_id, help_text)
            
        except Exception as e:
            logger.error(f"Error handling help callback: {e}")
    
    async def handle_digest_settings_callback(self, chat_id: str, db):
        """Handle digest settings callback - show digest mode selection menu"""
        try:
            from app.models import UserPreferences
            from sqlalchemy import select
            
            result = await db.execute(
                select(UserPreferences).where(UserPreferences.telegram_chat_id == chat_id)
            )
            user_prefs = result.scalar_one_or_none()
            
            if user_prefs:
                current_mode = user_prefs.telegram_digest_mode or 'all'
                await telegram_service.send_digest_settings_menu(chat_id, current_mode)
            else:
                await telegram_service.send_digest(chat_id, "❌ User not found. Use /start to configure.")
            
        except Exception as e:
            logger.error(f"Error handling digest settings callback: {e}")
            await telegram_service.send_digest(chat_id, "❌ Error getting settings. Please try again later.")
    
    async def handle_digest_mode_change(self, chat_id: str, new_mode: str, db):
        """Handle digest mode change callback"""
        try:
            from app.models import UserPreferences
            from sqlalchemy import select
            
            result = await db.execute(
                select(UserPreferences).where(UserPreferences.telegram_chat_id == chat_id)
            )
            user_prefs = result.scalar_one_or_none()
            
            if not user_prefs:
                await telegram_service.send_digest(chat_id, "❌ User not found. Use /start to configure.")
                return
            
            # Update digest mode
            # Use direct SQL update to avoid enum casting issues if enum doesn't exist
            from sqlalchemy import text
            await db.execute(
                text("UPDATE user_preferences SET telegram_digest_mode = :mode WHERE id = :user_id"),
                {"mode": new_mode, "user_id": user_prefs.id}
            )
            await db.commit()
            
            # Refresh the object to get updated value
            await db.refresh(user_prefs)
            
            # Send confirmation and show updated menu
            mode_text = "All News" if new_mode == "all" else "Tracked Only"
            confirmation_text = f"✅ Digest mode changed to: **{mode_text}**"
            await telegram_service.send_digest(chat_id, confirmation_text)
            
            # Show updated settings menu
            await telegram_service.send_digest_settings_menu(chat_id, new_mode)
            
        except Exception as e:
            logger.error(f"Error handling digest mode change: {e}")
            await telegram_service.send_digest(chat_id, "❌ Error changing settings. Please try again later.")
    
    async def handle_main_menu_callback(self, chat_id: str, db):
        """Handle main menu callback - return to start menu"""
        try:
            from app.bot.handlers import handle_start
            
            # Use the existing handle_start function to show main menu
            await handle_start(chat_id, None)
            
        except Exception as e:
            logger.error(f"Error handling main menu callback: {e}")
            await telegram_service.send_digest(chat_id, "❌ Error returning to main menu. Use /start")
    
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
