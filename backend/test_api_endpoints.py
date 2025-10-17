#!/usr/bin/env python3
"""
Test API endpoints for digests
"""

import asyncio
import aiohttp
import json

async def test_api_endpoints():
    """Test digest-related API endpoints"""
    
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        # Test webhook info endpoint
        try:
            async with session.get(f"{base_url}/api/v1/telegram/get-webhook-info") as response:
                if response.status == 200:
                    data = await response.json()
                    print("OK - Webhook info endpoint working:")
                    print(f"   Status: {data.get('status')}")
                    print(f"   Webhook info: {data.get('webhook_info', {})}")
                else:
                    print(f"ERROR - Webhook info endpoint failed: {response.status}")
        except Exception as e:
            print(f"ERROR - Error testing webhook info: {e}")
        
        # Test send test message endpoint
        try:
            test_chat_id = "1018308084"  # From logs
            async with session.post(
                f"{base_url}/api/v1/telegram/send-test-message",
                params={"chat_id": test_chat_id, "message": "API Test Message"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("OK - Send test message endpoint working:")
                    print(f"   Status: {data.get('status')}")
                else:
                    print(f"ERROR - Send test message endpoint failed: {response.status}")
        except Exception as e:
            print(f"ERROR - Error testing send message: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_endpoints())
