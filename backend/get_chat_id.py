#!/usr/bin/env python3
"""
Get chat ID from Telegram bot updates
"""

import asyncio
import aiohttp
from app.core.config import settings

async def get_updates():
    """Get updates from Telegram bot to find chat ID"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    updates = data.get('result', [])
                    
                    if updates:
                        print(f"📨 Found {len(updates)} updates:")
                        for update in updates:
                            if 'message' in update:
                                message = update['message']
                                chat = message['chat']
                                user = message.get('from', {})
                                print(f"   Chat ID: {chat['id']}")
                                print(f"   Chat Type: {chat['type']}")
                                print(f"   User: {user.get('first_name', '')} {user.get('last_name', '')}")
                                print(f"   Username: @{user.get('username', 'N/A')}")
                                print(f"   Message: {message.get('text', 'N/A')}")
                                print(f"   Date: {message.get('date', 'N/A')}")
                                print("   " + "-" * 40)
                    else:
                        print("📭 No updates found.")
                        print("💡 Please send /start to @short_news_sender_bot first!")
                        
                else:
                    print(f"❌ Error: {response.status}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

async def set_webhook():
    """Set webhook for the bot"""
    try:
        # For now, we'll use polling instead of webhook
        # Webhook would need a public URL
        print("🔧 Setting up bot for polling (no webhook needed for testing)")
        return True
    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Getting Chat ID from Telegram Bot")
    print("=" * 50)
    print("📋 Instructions:")
    print("1. Open Telegram")
    print("2. Search for @short_news_sender_bot")
    print("3. Send /start command")
    print("4. Run this script again")
    print("=" * 50)
    
    asyncio.run(get_updates())
