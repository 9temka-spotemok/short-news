#!/usr/bin/env python3
"""
Test script for digest generation
"""

import asyncio
from app.core.database import AsyncSessionLocal
from app.models import UserPreferences
from app.services.digest_service import DigestService
from sqlalchemy import select

async def test_digest_generation():
    """Test digest generation for a user"""
    async with AsyncSessionLocal() as db:
        # Get user preferences
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == '7e0556e1-2b75-43ff-b604-d09b767da3ad')
        )
        user_prefs = result.scalar_one_or_none()
        
        if not user_prefs:
            print("❌ User preferences not found")
            return
        
        print(f"✅ User found: {user_prefs.user_id}")
        print(f"   Digest enabled: {user_prefs.digest_enabled}")
        print(f"   Digest frequency: {user_prefs.digest_frequency}")
        print(f"   Digest format: {user_prefs.digest_format}")
        print(f"   Telegram enabled: {user_prefs.telegram_enabled}")
        print(f"   Telegram chat ID: {user_prefs.telegram_chat_id}")
        
        # Generate digest with extended date range
        digest_service = DigestService(db)
        
        try:
            # Try different periods
            for period in ['daily', 'weekly']:
                print(f"\n🔄 Testing {period} digest...")
                digest_data = await digest_service.generate_user_digest(
                    user_id=str(user_prefs.user_id),
                    period=period,
                    format_type=user_prefs.digest_format or "short"
                )
                
                print(f"   News count: {digest_data.get('news_count', 0)}")
                print(f"   Categories: {list(digest_data.get('categories', {}).keys())}")
                
                if digest_data.get('news_count', 0) > 0:
                    print(f"   ✅ {period.capitalize()} digest generated successfully!")
                    
                    # Format for display
                    digest_text = digest_service.format_digest_for_telegram(digest_data)
                    print(f"\n📰 {period.capitalize()} Digest:")
                    print("=" * 50)
                    print(digest_text[:500] + "..." if len(digest_text) > 500 else digest_text)
                    print("=" * 50)
                    break
                else:
                    print(f"   ⚠️ No news found for {period} digest")
        
        except Exception as e:
            print(f"❌ Error generating digest: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_digest_generation())
