#!/usr/bin/env python3
"""
Docker entry point script for Telegram bot
"""

import asyncio
import sys
import os
import signal
from pathlib import Path
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings

class TelegramBotRunner:
    """Telegram bot runner for Docker container"""
    
    def __init__(self):
        self.running = True
        self.polling_task = None
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.running = False
            if self.polling_task:
                self.polling_task.cancel()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def check_health(self):
        """Check if bot is healthy"""
        try:
            import aiohttp
            
            if not settings.TELEGRAM_BOT_TOKEN:
                logger.error("TELEGRAM_BOT_TOKEN not configured!")
                return False
            
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            bot_info = result.get("result", {})
                            logger.info(f"Bot health check passed: @{bot_info.get('username')}")
                            return True
                        else:
                            logger.error(f"Telegram API error: {result}")
                            return False
                    else:
                        logger.error(f"HTTP error: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def run_polling(self):
        """Run telegram bot polling"""
        try:
            from app.services.telegram_service import telegram_service
            from scripts.telegram_polling import TelegramPolling
            
            # Wait for database and redis to be ready
            await self.wait_for_dependencies()
            
            # Check bot health
            if not await self.check_health():
                logger.error("Bot health check failed, exiting...")
                return
            
            # Start polling
            logger.info("🤖 Starting Telegram bot polling...")
            polling = TelegramPolling()
            
            # Override the polling stop method to use our running flag
            original_stop = polling.stop_polling
            def stop_polling():
                self.running = False
                original_stop()
            polling.stop_polling = stop_polling
            
            # Start polling with our running flag
            polling.running = True
            while self.running and polling.running:
                try:
                    updates = await polling.get_updates()
                    
                    for update in updates:
                        await polling.process_update(update)
                    
                    # Small delay to prevent busy waiting
                    await asyncio.sleep(0.1)
                    
                except asyncio.CancelledError:
                    logger.info("Polling cancelled")
                    break
                except Exception as e:
                    logger.error(f"Polling error: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
            
            logger.info("🛑 Telegram bot polling stopped")
            
        except Exception as e:
            logger.error(f"Error running polling: {e}")
            raise
    
    async def wait_for_dependencies(self, max_retries=30, delay=2):
        """Wait for database and redis to be ready"""
        logger.info("⏳ Waiting for dependencies...")
        
        for attempt in range(max_retries):
            try:
                # Test database connection
                from app.core.database import AsyncSessionLocal
                from sqlalchemy import text
                async with AsyncSessionLocal() as db:
                    await db.execute(text("SELECT 1"))
                
                # Test redis connection
                import redis
                redis_client = redis.from_url(settings.REDIS_URL)
                redis_client.ping()
                
                logger.info("✅ Dependencies are ready")
                return
                
            except Exception as e:
                logger.warning(f"Dependencies not ready (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    logger.error("❌ Dependencies failed to become ready")
                    raise
    
    async def run(self):
        """Main run method"""
        logger.info("🚀 Starting Telegram Bot Container")
        logger.info("=" * 50)
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Configure logging
        logger.remove()
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO"
        )
        
        # Check configuration
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN not configured!")
            logger.error("Please set the TELEGRAM_BOT_TOKEN environment variable")
            sys.exit(1)
        
        logger.info(f"✅ Bot token configured: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
        logger.info(f"✅ Database URL: {settings.DATABASE_URL}")
        logger.info(f"✅ Redis URL: {settings.REDIS_URL}")
        
        try:
            # Start polling
            self.polling_task = asyncio.create_task(self.run_polling())
            await self.polling_task
            
        except KeyboardInterrupt:
            logger.info("🛑 Received keyboard interrupt")
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            logger.info("🛑 Telegram Bot Container stopped")

async def main():
    """Main entry point"""
    runner = TelegramBotRunner()
    await runner.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Container stopped by user")
    except Exception as e:
        print(f"❌ Container failed: {e}")
        sys.exit(1)
