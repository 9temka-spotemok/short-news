#!/usr/bin/env python3
"""
Test script for Telegram bot
"""

import asyncio
from app.services.telegram_service import telegram_service
from app.core.config import settings

async def test_telegram_bot():
    """Test Telegram bot functionality"""
    print(f"🤖 Testing Telegram bot: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
    
    try:
        # Test sending a message to your chat ID
        # You need to start a conversation with @short_news_sender_bot first
        chat_id = "123456789"  # Replace with your actual chat ID
        
        message = """🧪 **Test message from AI Competitor Insight Hub**

✅ Telegram bot configured and working!

📊 **System Status:**
- Backend API: ✅ Running
- Celery Worker: ✅ Running  
- Digest Generation: ✅ Working
- Telegram Integration: ✅ Working

🚀 Now you can receive digests directly in Telegram!"""
        
        print(f"📤 Sending message to chat {chat_id}...")
        result = await telegram_service.send_digest(chat_id, message)
        
        if result:
            print("✅ Message sent successfully!")
        else:
            print("❌ Error sending message")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def get_bot_info():
    """Get bot information"""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    bot_info = data.get('result', {})
                    print(f"🤖 Bot Info:")
                    print(f"   Name: {bot_info.get('first_name')}")
                    print(f"   Username: @{bot_info.get('username')}")
                    print(f"   ID: {bot_info.get('id')}")
                    print(f"   Can join groups: {bot_info.get('can_join_groups')}")
                    print(f"   Can read all group messages: {bot_info.get('can_read_all_group_messages')}")
                    return True
                else:
                    print(f"❌ Error getting bot info: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Telegram Bot Setup")
    print("=" * 50)
    
    # First get bot info
    asyncio.run(get_bot_info())
    
    print("\n" + "=" * 50)
    
    # Then test sending message
    asyncio.run(test_telegram_bot())
