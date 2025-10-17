#!/usr/bin/env python3
"""
Simple test for Telegram bot callbacks without DB
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.telegram_service import telegram_service

async def test_message_sending():
    """Test message sending functionality"""
    chat_id = "1018308084"
    
    print("🧪 Testing message sending...")
    
    # Test simple message
    test_message = "🧪 **Test Message**\n\nThis is a test message from the refactored bot!"
    success = await telegram_service.send_digest(chat_id, test_message)
    
    if success:
        print("✅ Simple message sent successfully!")
    else:
        print("❌ Failed to send simple message")
    
    # Test message with keyboard
    print("\n🔧 Testing message with keyboard...")
    keyboard_message = "📱 **Test Keyboard**\n\nChoose an option:"
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
        print("✅ Message with keyboard sent successfully!")
    else:
        print("❌ Failed to send message with keyboard")

async def test_celery_task():
    """Test Celery task creation"""
    print("\n🔄 Testing Celery task creation...")
    
    try:
        from app.tasks.digest import generate_user_digest
        
        # Create task
        task = generate_user_digest.delay('7e0556e1-2b75-43ff-b604-d09b767da3ad', 'daily')
        print(f"✅ Task created: {task.id}")
        print(f"   Task state: {task.state}")
        
        # Wait a bit
        import time
        time.sleep(3)
        
        print(f"   Task state after 3s: {task.state}")
        
        if task.state == 'SUCCESS':
            print("✅ Task completed successfully!")
        elif task.state == 'FAILURE':
            print(f"❌ Task failed: {task.info}")
        else:
            print(f"⏳ Task still running: {task.state}")
            
    except Exception as e:
        print(f"❌ Error creating task: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function"""
    print("🚀 Simple Telegram Bot Test")
    print("=" * 50)
    
    await test_message_sending()
    await test_celery_task()
    
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

