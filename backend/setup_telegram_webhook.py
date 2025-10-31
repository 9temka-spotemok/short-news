#!/usr/bin/env python3
"""
Railway Telegram Bot Webhook Setup
Configure webhook for Telegram bot on Railway
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.telegram_service import TelegramService
from app.core.config import settings
from loguru import logger

async def setup_webhook():
    """Setup Telegram webhook for Railway deployment"""
    print("🤖 Setting up Telegram Bot Webhook for Railway")
    print("=" * 60)
    
    # Check if bot token is configured
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not configured!")
        print("Please set TELEGRAM_BOT_TOKEN environment variable")
        return False
    
    print(f"✅ Bot token configured: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
    
    # Get webhook URL from environment or prompt user
    webhook_url = os.environ.get("WEBHOOK_URL")
    
    if not webhook_url:
        print("\n📝 Please provide your Railway webhook URL:")
        print("Format: https://your-web-service.up.railway.app/api/v1/telegram/webhook")
        webhook_url = input("Webhook URL: ").strip()
    
    if not webhook_url:
        print("❌ Webhook URL is required!")
        return False
    
    if not webhook_url.startswith("https://"):
        print("❌ Webhook URL must start with https://")
        return False
    
    print(f"🔗 Setting webhook: {webhook_url}")
    
    # Initialize Telegram service
    telegram_service = TelegramService()
    
    # Set webhook
    success = await telegram_service.set_webhook(webhook_url)
    
    if success:
        print("✅ Webhook set successfully!")
        print(f"🔗 Webhook URL: {webhook_url}")
        print("\n📋 Next steps:")
        print("1. Test your bot by sending /start command")
        print("2. Check Railway logs for webhook events")
        print("3. Verify that messages are being processed")
        return True
    else:
        print("❌ Failed to set webhook!")
        print("Check your bot token and webhook URL")
        return False

async def delete_webhook():
    """Delete Telegram webhook"""
    print("🗑️  Deleting Telegram Bot Webhook")
    print("=" * 40)
    
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not configured!")
        return False
    
    telegram_service = TelegramService()
    success = await telegram_service.delete_webhook()
    
    if success:
        print("✅ Webhook deleted successfully!")
        print("Bot will now use polling mode")
        return True
    else:
        print("❌ Failed to delete webhook!")
        return False

async def check_webhook():
    """Check current webhook status"""
    print("🔍 Checking Telegram Bot Webhook Status")
    print("=" * 50)
    
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not configured!")
        return False
    
    telegram_service = TelegramService()
    webhook_info = await telegram_service.get_webhook_info()
    
    if webhook_info:
        print("✅ Webhook information retrieved:")
        print(f"URL: {webhook_info.get('url', 'Not set')}")
        print(f"Pending updates: {webhook_info.get('pending_update_count', 0)}")
        print(f"Last error: {webhook_info.get('last_error_message', 'None')}")
        print(f"Last error date: {webhook_info.get('last_error_date', 'None')}")
        return True
    else:
        print("❌ Failed to get webhook information!")
        return False

async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python setup_telegram_webhook.py <command>")
        print("Commands:")
        print("  setup   - Setup webhook for Railway")
        print("  delete  - Delete webhook (use polling)")
        print("  check   - Check webhook status")
        return
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        await setup_webhook()
    elif command == "delete":
        await delete_webhook()
    elif command == "check":
        await check_webhook()
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: setup, delete, check")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"\n💥 Error: {e}")
        sys.exit(1)
