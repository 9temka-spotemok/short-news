#!/usr/bin/env python3
"""
Test script to simulate digest button clicks
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

async def simulate_digest_button_click():
    """Simulate clicking digest buttons"""
    chat_id = "1018308084"
    
    print("🎯 Simulating digest button clicks...")
    
    try:
        # First, send a message with keyboard
        keyboard_message = "📱 **Digest Test**\n\nClick the buttons below to test digest generation:"
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📅 Дневной дайджест", "callback_data": "digest_daily"},
                    {"text": "📊 Недельный дайджест", "callback_data": "digest_weekly"}
                ],
                [
                    {"text": "⚙️ Настройки", "callback_data": "settings_view"},
                    {"text": "📚 Помощь", "callback_data": "help"}
                ]
            ]
        }
        
        success = await telegram_service.send_message_with_keyboard(chat_id, keyboard_message, keyboard)
        if success:
            print("✅ Message with keyboard sent!")
        else:
            print("❌ Failed to send message with keyboard")
            return
        
        # Now simulate button clicks
        print("\n🔄 Simulating button clicks...")
        
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
                await telegram_service.send_digest(chat_id, "❌ Пользователь не найден или Telegram не настроен.")
                return
            
            print(f"✅ User found: {user_prefs.user_id}")
            
            # Simulate daily digest button click
            print("\n📅 Simulating daily digest button click...")
            await telegram_service.send_digest(chat_id, "🔄 Генерирую дневной дайджест...")
            
            task = generate_user_digest.delay(str(user_prefs.user_id), "daily")
            print(f"✅ Daily digest task created: {task.id}")
            
            # Simulate weekly digest button click
            print("\n📊 Simulating weekly digest button click...")
            await telegram_service.send_digest(chat_id, "🔄 Генерирую недельный дайджест...")
            
            task = generate_user_digest.delay(str(user_prefs.user_id), "weekly")
            print(f"✅ Weekly digest task created: {task.id}")
            
            # Wait and check task status
            import time
            time.sleep(5)
            
            print(f"\n📊 Task states after 5 seconds:")
            print(f"   Daily task: {task.state}")
            
            if task.state == 'SUCCESS':
                print("✅ Digest generated successfully!")
            elif task.state == 'FAILURE':
                print(f"❌ Task failed: {task.info}")
            else:
                print(f"⏳ Task still running: {task.state}")
            
            # Send completion message
            await telegram_service.send_digest(chat_id, "✅ Дайджесты генерируются в фоне и будут отправлены в ближайшее время!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Send error message to user
        await telegram_service.send_digest(chat_id, f"❌ Ошибка при тестировании: {str(e)}")

async def main():
    """Main test function"""
    print("🚀 Digest Buttons Test")
    print("=" * 50)
    
    await simulate_digest_button_click()
    
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

