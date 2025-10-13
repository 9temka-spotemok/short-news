"""
Test news API endpoint
"""

import asyncio
import httpx


async def test_api():
    """Test news API"""
    async with httpx.AsyncClient() as client:
        # Test news endpoint
        print("Testing GET /api/v1/news/ ...")
        try:
            response = await client.get("http://localhost:8000/api/v1/news/", params={"limit": 5})
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Success!")
                print(f"   Total news: {data['total']}")
                print(f"   Items returned: {len(data['items'])}")
                
                if data['items']:
                    print(f"\n   First news item:")
                    item = data['items'][0]
                    print(f"   - Title: {item['title'][:60]}...")
                    print(f"   - Category: {item.get('category', 'N/A')}")
                    print(f"   - Company: {item.get('company', {}).get('name', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_api())



