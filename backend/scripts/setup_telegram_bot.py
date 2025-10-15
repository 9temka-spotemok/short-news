#!/usr/bin/env python3
"""
Quick setup script for Telegram bot
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


async def setup_bot():
    """Setup Telegram bot with webhook"""
    print("🚀 Setting up Telegram Bot for AI Competitor Insight Hub")
    print("=" * 60)
    
    # Check if token is configured
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not configured!")
        print("Please add your bot token to .env file:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        return False
    
    print(f"✅ Bot token configured: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
    
    # Test bot token
    print("\n🔍 Testing bot token...")
    try:
        import aiohttp
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("ok"):
                        bot_info = result.get("result", {})
                        print(f"✅ Bot is active: @{bot_info.get('username')}")
                        print(f"   Name: {bot_info.get('first_name')}")
                        print(f"   ID: {bot_info.get('id')}")
                    else:
                        print(f"❌ Invalid bot token: {result}")
                        return False
                else:
                    print(f"❌ HTTP error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Error testing bot: {e}")
        return False
    
    # Setup webhook (optional)
    print("\n🔗 Webhook setup (optional)...")
    webhook_url = input("Enter webhook URL (or press Enter to skip): ").strip()
    
    if webhook_url:
        print(f"Setting webhook to: {webhook_url}")
        success = await telegram_service.set_webhook(webhook_url)
        if success:
            print("✅ Webhook set successfully!")
            
            # Get webhook info
            info = await telegram_service.get_webhook_info()
            print(f"   URL: {info.get('url', 'Not set')}")
            print(f"   Pending updates: {info.get('pending_update_count', 0)}")
        else:
            print("❌ Failed to set webhook")
    else:
        print("⏭️ Skipping webhook setup (using polling mode)")
    
    # Test message sending
    print("\n📤 Test message sending...")
    chat_id = input("Enter your Chat ID for testing (or press Enter to skip): ").strip()
    
    if chat_id:
        test_message = (
            "🎉 **Telegram Bot Setup Complete!**\n\n"
            "Your AI Competitor Insight Hub bot is now ready to use!\n\n"
            "✅ Bot configuration: OK\n"
            "✅ Webhook setup: OK\n"
            "✅ Message sending: OK\n\n"
            "You can now receive personalized news digests!"
        )
        
        success = await telegram_service.send_digest(chat_id, test_message)
        if success:
            print("✅ Test message sent successfully!")
        else:
            print("❌ Failed to send test message")
    else:
        print("⏭️ Skipping test message")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Setup Summary:")
    print("=" * 60)
    print("✅ Bot token: Configured")
    print("✅ Bot status: Active")
    if webhook_url:
        print("✅ Webhook: Configured")
    else:
        print("⚠️ Webhook: Not configured (using polling)")
    
    print("\n🎯 Next steps:")
    print("1. Start your backend server: python main.py")
    print("2. Start Celery worker: celery -A celery_app worker --loglevel=info")
    print("3. Start Celery beat: celery -A celery_app beat --loglevel=info")
    print("4. Test bot commands in Telegram")
    
    print("\n📚 Commands to test:")
    print("- /start - Get your Chat ID and welcome message")
    print("- /help - Show available commands")
    print("- /digest - Get a personalized digest")
    print("- /settings - View current settings")
    
    return True


async def main():
    """Main setup function"""
    try:
        await setup_bot()
    except KeyboardInterrupt:
        print("\n\n⏹️ Setup interrupted by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        logger.exception("Setup error")


if __name__ == "__main__":
    asyncio.run(main())
