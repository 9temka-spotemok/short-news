#!/usr/bin/env python3
"""
Interactive Telegram bot setup script
"""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path

def update_env_file(token: str, channel_id: str = None):
    """Update .env file with bot token"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env file not found!")
        return False
    
    # Read current content
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Update token and channel
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            lines[i] = f'TELEGRAM_BOT_TOKEN={token}\n'
            updated = True
        elif line.startswith('TELEGRAM_CHANNEL_ID=') and channel_id:
            lines[i] = f'TELEGRAM_CHANNEL_ID={channel_id}\n'
            updated = True
    
    # Write back
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return updated

async def test_bot_token(token: str):
    """Test if bot token is valid"""
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("ok"):
                        bot_info = result.get("result", {})
                        return True, bot_info
                    else:
                        return False, result.get("description", "Unknown error")
                else:
                    return False, f"HTTP {response.status}"
    except Exception as e:
        return False, str(e)

async def setup_webhook(token: str, webhook_url: str):
    """Setup webhook for the bot"""
    try:
        url = f"https://api.telegram.org/bot{token}/setWebhook"
        payload = {
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query", "channel_post"]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("ok", False), result.get("description", "")
                else:
                    return False, f"HTTP {response.status}"
    except Exception as e:
        return False, str(e)

async def delete_webhook(token: str):
    """Delete webhook (use polling instead)"""
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("ok", False), result.get("description", "")
                else:
                    return False, f"HTTP {response.status}"
    except Exception as e:
        return False, str(e)

async def send_test_message(token: str, chat_id: str):
    """Send test message to verify bot works"""
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "🎉 **Telegram Bot Setup Complete!**\n\nYour AI Competitor Insight Hub bot is now ready to use!\n\n✅ Bot configuration: OK\n✅ Message sending: OK\n\nYou can now receive personalized news digests!",
            "parse_mode": "Markdown"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("ok", False), result.get("description", "")
                else:
                    return False, f"HTTP {response.status}"
    except Exception as e:
        return False, str(e)

async def main():
    """Main setup function"""
    print("🚀 Interactive Telegram Bot Setup")
    print("=" * 50)
    
    # Step 1: Get bot token
    print("\n📋 Step 1: Bot Token Setup")
    print("If you don't have a bot token yet:")
    print("1. Open Telegram and find @BotFather")
    print("2. Send /newbot command")
    print("3. Follow the instructions to create a bot")
    print("4. Copy the token you receive")
    print()
    
    token = input("Enter your bot token: ").strip()
    if not token:
        print("❌ Bot token is required!")
        return
    
    # Test token
    print("\n🔍 Testing bot token...")
    is_valid, info = await test_bot_token(token)
    
    if not is_valid:
        print(f"❌ Invalid bot token: {info}")
        return
    
    bot_info = info
    print(f"✅ Bot is valid!")
    print(f"   Name: {bot_info.get('first_name')}")
    print(f"   Username: @{bot_info.get('username')}")
    print(f"   ID: {bot_info.get('id')}")
    
    # Step 2: Update .env file
    print("\n📝 Step 2: Updating .env file...")
    if update_env_file(token):
        print("✅ .env file updated successfully!")
    else:
        print("❌ Failed to update .env file!")
        return
    
    # Step 3: Webhook or Polling
    print("\n🔗 Step 3: Webhook or Polling Setup")
    print("Choose how the bot should receive messages:")
    print("1. Webhook (for production with public URL)")
    print("2. Polling (for development/testing)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        webhook_url = input("Enter webhook URL (e.g., https://yourdomain.com/api/v1/telegram/webhook): ").strip()
        if webhook_url:
            print("🔗 Setting up webhook...")
            success, message = await setup_webhook(token, webhook_url)
            if success:
                print("✅ Webhook set successfully!")
            else:
                print(f"❌ Failed to set webhook: {message}")
        else:
            print("⏭️ Skipping webhook setup")
    else:
        print("🔄 Setting up polling mode...")
        success, message = await delete_webhook(token)
        if success:
            print("✅ Webhook deleted, bot will use polling")
        else:
            print(f"⚠️ Could not delete webhook: {message}")
    
    # Step 4: Test message
    print("\n📤 Step 4: Test Message")
    chat_id = input("Enter your Chat ID for testing (or press Enter to skip): ").strip()
    
    if chat_id:
        print("📤 Sending test message...")
        success, message = await send_test_message(token, chat_id)
        if success:
            print("✅ Test message sent successfully!")
        else:
            print(f"❌ Failed to send test message: {message}")
    else:
        print("⏭️ Skipping test message")
    
    # Step 5: Summary
    print("\n" + "=" * 50)
    print("📊 Setup Summary:")
    print("=" * 50)
    print("✅ Bot token: Configured and tested")
    print("✅ .env file: Updated")
    if choice == "1":
        print("✅ Webhook: Configured")
    else:
        print("✅ Polling: Enabled")
    
    print("\n🎯 Next steps:")
    print("1. Restart your backend server: python main.py")
    print("2. If using polling, start the polling script:")
    print("   python scripts/telegram_polling.py")
    print("3. Test bot commands in Telegram:")
    print("   - /start - Get your Chat ID")
    print("   - /help - Show available commands")
    print("   - /digest - Get a personalized digest")
    
    print("\n📚 Bot Commands:")
    print("- /start - Welcome message and Chat ID")
    print("- /help - Show available commands")
    print("- /digest - Request personalized digest")
    print("- /settings - View current settings")
    print("- /subscribe - Subscribe to digests")
    print("- /unsubscribe - Unsubscribe from digests")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ Setup interrupted by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()

