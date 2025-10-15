#!/usr/bin/env python3
"""
Telegram bot testing script
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
from loguru import logger


async def test_bot_token():
    """Test if bot token is valid"""
    print("🔍 Testing Telegram bot token...")
    
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set in environment")
        return False
    
    # Test bot info
    import aiohttp
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("ok"):
                        bot_info = result.get("result", {})
                        print(f"✅ Bot token valid!")
                        print(f"   Bot name: {bot_info.get('first_name')}")
                        print(f"   Bot username: @{bot_info.get('username')}")
                        print(f"   Bot ID: {bot_info.get('id')}")
                        return True
                    else:
                        print(f"❌ Telegram API error: {result}")
                        return False
                else:
                    print(f"❌ HTTP error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Error testing bot token: {e}")
        return False


async def test_send_message():
    """Test sending a message"""
    print("\n📤 Testing message sending...")
    
    # Get chat ID from user
    chat_id = input("Enter your Telegram Chat ID (send /start to bot to get it): ").strip()
    
    if not chat_id:
        print("❌ Chat ID is required")
        return False
    
    test_message = (
        "🧪 **Test Message from AI Competitor Insight Hub**\n\n"
        "If you received this message, your Telegram bot is working correctly!\n\n"
        "✅ Bot configuration: OK\n"
        "✅ Message sending: OK\n"
        "✅ Markdown formatting: OK\n\n"
        "You can now receive personalized news digests!"
    )
    
    try:
        success = await telegram_service.send_digest(chat_id, test_message)
        if success:
            print("✅ Test message sent successfully!")
            return True
        else:
            print("❌ Failed to send test message")
            return False
    except Exception as e:
        print(f"❌ Error sending test message: {e}")
        return False


async def test_webhook():
    """Test webhook functionality"""
    print("\n🔗 Testing webhook...")
    
    webhook_url = input("Enter your webhook URL (or press Enter to skip): ").strip()
    
    if not webhook_url:
        print("⏭️ Skipping webhook test")
        return True
    
    try:
        # Set webhook
        success = await telegram_service.set_webhook(webhook_url)
        if success:
            print("✅ Webhook set successfully!")
            
            # Get webhook info
            info = await telegram_service.get_webhook_info()
            print(f"   Webhook URL: {info.get('url', 'Not set')}")
            print(f"   Pending updates: {info.get('pending_update_count', 0)}")
            
            return True
        else:
            print("❌ Failed to set webhook")
            return False
    except Exception as e:
        print(f"❌ Error testing webhook: {e}")
        return False


async def test_commands():
    """Test bot commands"""
    print("\n🤖 Testing bot commands...")
    
    chat_id = input("Enter your Telegram Chat ID for command testing: ").strip()
    
    if not chat_id:
        print("❌ Chat ID is required")
        return False
    
    # Test /start command
    print("Testing /start command...")
    from app.bot.handlers import handle_start
    response = await handle_start(chat_id, "test_user")
    if response == "":
        print("✅ /start command handled (message sent with keyboard)")
    else:
        print(f"⚠️ /start command response: {response}")
    
    # Test /help command
    print("Testing /help command...")
    from app.bot.handlers import handle_help
    response = await handle_help(chat_id)
    print(f"✅ /help command response: {response[:100]}...")
    
    return True


async def main():
    """Main testing function"""
    print("🚀 Telegram Bot Testing Script")
    print("=" * 50)
    
    tests = [
        ("Bot Token", test_bot_token),
        ("Send Message", test_send_message),
        ("Webhook", test_webhook),
        ("Commands", test_commands),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print("\n\n⏹️ Testing interrupted by user")
            break
        except Exception as e:
            print(f"❌ Unexpected error in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your Telegram bot is ready to use.")
    else:
        print("⚠️ Some tests failed. Check the configuration and try again.")


if __name__ == "__main__":
    asyncio.run(main())
