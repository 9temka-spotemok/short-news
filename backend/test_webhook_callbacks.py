#!/usr/bin/env python3
"""
Test webhook callbacks for digest buttons
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import aiohttp

async def test_webhook_callback():
    """Test webhook callback for digest buttons"""
    
    # Simulate callback query from Telegram
    callback_data = {
        "update_id": 123456789,
        "callback_query": {
            "id": "test_callback_id",
            "from": {
                "id": 1018308084,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "message": {
                "message_id": 123,
                "from": {
                    "id": 8358550051,
                    "is_bot": True,
                    "first_name": "short-news",
                    "username": "short_news_sender_bot"
                },
                "chat": {
                    "id": 1018308084,
                    "first_name": "Test",
                    "username": "testuser",
                    "type": "private"
                },
                "date": 1697568000,
                "text": "Test message"
            },
            "data": "digest_daily"
        }
    }
    
    print("🧪 Testing webhook callback for daily digest...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/api/v1/telegram/webhook",
                json=callback_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Response status: {response.status}")
                result = await response.text()
                print(f"Response: {result}")
                
                if response.status == 200:
                    print("✅ Webhook callback processed successfully!")
                else:
                    print(f"❌ Webhook callback failed: {response.status}")
                    
    except Exception as e:
        print(f"❌ Error testing webhook: {e}")
        import traceback
        traceback.print_exc()

async def test_weekly_digest_callback():
    """Test webhook callback for weekly digest"""
    
    callback_data = {
        "update_id": 123456790,
        "callback_query": {
            "id": "test_callback_id_2",
            "from": {
                "id": 1018308084,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "message": {
                "message_id": 124,
                "from": {
                    "id": 8358550051,
                    "is_bot": True,
                    "first_name": "short-news",
                    "username": "short_news_sender_bot"
                },
                "chat": {
                    "id": 1018308084,
                    "first_name": "Test",
                    "username": "testuser",
                    "type": "private"
                },
                "date": 1697568000,
                "text": "Test message"
            },
            "data": "digest_weekly"
        }
    }
    
    print("\n🧪 Testing webhook callback for weekly digest...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/api/v1/telegram/webhook",
                json=callback_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Response status: {response.status}")
                result = await response.text()
                print(f"Response: {result}")
                
                if response.status == 200:
                    print("✅ Weekly digest webhook processed successfully!")
                else:
                    print(f"❌ Weekly digest webhook failed: {response.status}")
                    
    except Exception as e:
        print(f"❌ Error testing weekly webhook: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function"""
    print("🚀 Webhook Callback Test")
    print("=" * 50)
    
    await test_webhook_callback()
    await test_weekly_digest_callback()
    
    print("\n" + "=" * 50)
    print("✅ Webhook test completed!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

