#!/usr/bin/env python3
"""
Script to fix user preferences for Telegram digest testing
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.database import AsyncSessionLocal
from app.models import UserPreferences
from sqlalchemy import select
import uuid

async def fix_user_preferences():
    """Fix user preferences for digest testing"""
    
    async with AsyncSessionLocal() as db:
        # Find user with telegram enabled
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.telegram_enabled == True)
        )
        user_prefs = result.scalar_one_or_none()
        
        if not user_prefs:
            print("❌ No user with Telegram enabled found")
            return
        
        print(f"✅ Found user: {user_prefs.user_id}")
        print(f"   Telegram Chat ID: {user_prefs.telegram_chat_id}")
        
        # Update preferences
        user_prefs.subscribed_companies = [
            uuid.UUID('a25ff382-3354-412b-be7f-dad5f1748eee'),  # OpenAI
            uuid.UUID('0b867722-f397-4f40-9bc9-e9f9163d0ec6'),  # Anthropic
            uuid.UUID('e0afb6e7-bddf-49f8-afa2-a182d7acd0b8'),  # Google
            uuid.UUID('6b77b1b7-1c56-4a61-ab96-b548c01baba8'),  # Meta
            uuid.UUID('e4ff3931-6a27-4cdc-bc92-6ed077b041e8'),  # Microsoft
        ]
        
        user_prefs.interested_categories = [
            'product_update',
            'strategic_announcement', 
            'model_release',
            'technical_update',
            'security_update'
        ]
        
        user_prefs.digest_frequency = 'daily'
        user_prefs.digest_enabled = True
        
        await db.commit()
        
        print("✅ User preferences updated:")
        print(f"   Subscribed companies: {len(user_prefs.subscribed_companies)}")
        print(f"   Interested categories: {len(user_prefs.interested_categories)}")
        print(f"   Digest frequency: {user_prefs.digest_frequency}")
        print(f"   Digest enabled: {user_prefs.digest_enabled}")

if __name__ == "__main__":
    asyncio.run(fix_user_preferences())
