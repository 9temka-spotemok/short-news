#!/usr/bin/env python3
"""
Test script for Telegram bot callbacks
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.telegram_service import telegram_service
from app.core.database import AsyncSessionLocal
from app.models import UserPreferences
from app.tasks.digest import generate_user_digest
from sqlalchemy import select
from loguru import logger

async def test_digest_callback():
    """Test digest callback functionality"""
    chat_id = "1018308084"
    
    print("🧪 Testing digest callback functionality...")
    
    try:
        # Test user lookup
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(UserPreferences).where(
                    UserPreferences.telegram_chat_id == chat_id,
                    UserPreferences.telegram_enabled == True
                )
            )
            user_prefs = result.scalar_one_or_none()
            
            if not user_prefs:
                print("❌ User not found or Telegram not enabled")
                return
            
            print(f"✅ User found: {user_prefs.user_id}")
            print(f"   Telegram enabled: {user_prefs.telegram_enabled}")
            print(f"   Digest enabled: {user_prefs.digest_enabled}")
            print(f"   Chat ID: {user_prefs.telegram_chat_id}")
            
            # Test digest generation
            print("\n🔄 Testing digest generation...")
            task = generate_user_digest.delay(str(user_prefs.user_id), "daily")
            print(f"✅ Task created: {task.id}")
            
            # Wait for task completion
            import time
            time.sleep(5)
            
            print(f"📊 Task state: {task.state}")
            
            if task.state == 'SUCCESS':
                print("✅ Digest generated successfully!")
                result = task.result
                print(f"   News count: {result.get('news_count', 'N/A')}")
            elif task.state == 'FAILURE':
                print(f"❌ Task failed: {task.info}")
                if hasattr(task, 'traceback'):
                    print(f"   Traceback: {task.traceback}")
            else:
                print(f"⏳ Task still running: {task.state}")
            
            # Test message sending
            print("\n📤 Testing message sending...")
            test_message = "🧪 **Test Message**\n\nThis is a test message from the refactored bot!"
            success = await telegram_service.send_digest(chat_id, test_message)
            
            if success:
                print("✅ Test message sent successfully!")
            else:
                print("❌ Failed to send test message")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_callback_handlers():
    """Test callback handlers directly"""
    chat_id = "1018308084"
    
    print("\n🔧 Testing callback handlers...")
    
    # Import the polling class
    from scripts.telegram_polling import TelegramPolling
    
    polling = TelegramPolling()
    
    try:
        async with AsyncSessionLocal() as db:
            # Test digest callback
            print("📅 Testing daily digest callback...")
            await polling.handle_digest_callback(chat_id, "daily", db)
            
            print("📊 Testing weekly digest callback...")
            await polling.handle_digest_callback(chat_id, "weekly", db)
            
            print("⚙️ Testing settings callback...")
            await polling.handle_settings_callback(chat_id, db)
            
            print("📚 Testing help callback...")
            await polling.handle_help_callback(chat_id, db)
            
    except Exception as e:
        print(f"❌ Error testing callbacks: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function"""
    print("🚀 Telegram Bot Callback Test")
    print("=" * 50)
    
    await test_digest_callback()
    await test_callback_handlers()
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

