#!/usr/bin/env python3
"""
Test digest generation to see full output
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.database import AsyncSessionLocal
from app.services.digest_service import DigestService
from app.models import UserPreferences
from sqlalchemy import select

async def test_digest_generation():
    """Test digest generation"""
    
    async with AsyncSessionLocal() as db:
        # Find user with telegram enabled
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.telegram_enabled == True)
        )
        user_prefs = result.scalar_one_or_none()
        
        if not user_prefs:
            print("No user with Telegram enabled found")
            return
        
        print(f"Testing digest for user: {user_prefs.user_id}")
        print(f"Telegram Chat ID: {user_prefs.telegram_chat_id}")
        print(f"Subscribed companies: {len(user_prefs.subscribed_companies) if user_prefs.subscribed_companies else 0}")
        print(f"Interested categories: {len(user_prefs.interested_categories) if user_prefs.interested_categories else 0}")
        
        # Generate digest
        digest_service = DigestService(db)
        digest_data = await digest_service.generate_user_digest(
            user_id=str(user_prefs.user_id),
            period="daily",
            format_type="short"
        )
        
        print(f"\nDigest generated: {digest_data['news_count']} news items")
        print(f"Categories: {list(digest_data['categories'].keys())}")
        
        # Format for Telegram
        telegram_text = digest_service.format_digest_for_telegram(digest_data)
        
        print(f"\nTelegram message length: {len(telegram_text)} characters")
        print(f"Message preview (first 500 chars):")
        print("-" * 50)
        print(telegram_text[:500])
        print("-" * 50)
        
        # Test message splitting
        from app.services.telegram_service import telegram_service
        messages = telegram_service._split_message(telegram_text)
        print(f"\nMessage will be split into {len(messages)} parts:")
        for i, msg in enumerate(messages, 1):
            print(f"Part {i}: {len(msg)} characters")

if __name__ == "__main__":
    asyncio.run(test_digest_generation())