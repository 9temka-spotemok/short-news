#!/usr/bin/env python3
"""
Test script for digest scheduler
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from loguru import logger
from datetime import datetime

from app.core.database import AsyncSessionLocal
from app.models import UserPreferences
from app.tasks.digest import _is_user_due_now_precise


async def test_digest_scheduler():
    """Test digest scheduler logic"""
    
    async with AsyncSessionLocal() as db:
        # Get all users with digest enabled
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.digest_enabled == True)
        )
        users = result.scalars().all()
        
        logger.info(f"Found {len(users)} users with digest enabled")
        
        for user_prefs in users:
            logger.info(f"\n--- User {user_prefs.user_id} ---")
            logger.info(f"Frequency: {user_prefs.digest_frequency}")
            logger.info(f"Telegram enabled: {user_prefs.telegram_enabled}")
            logger.info(f"Chat ID: {user_prefs.telegram_chat_id}")
            logger.info(f"Custom schedule: {user_prefs.digest_custom_schedule}")
            logger.info(f"Timezone: {user_prefs.timezone}")
            
            # Test if user is due now
            is_due = _is_user_due_now_precise(user_prefs, user_prefs.digest_frequency)
            logger.info(f"Is due now: {is_due}")
            
            if is_due:
                logger.info("✅ This user should receive a digest now!")
            else:
                logger.info("⏰ This user is not due for a digest yet")


async def test_specific_user_digest():
    """Test generating digest for a specific user"""
    
    async with AsyncSessionLocal() as db:
        # Get first user with digest enabled
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.digest_enabled == True).limit(1)
        )
        user_prefs = result.scalar_one_or_none()
        
        if not user_prefs:
            logger.info("No users with digest enabled found")
            return
        
        logger.info(f"Testing digest generation for user {user_prefs.user_id}")
        
        # Import and test digest generation
        from app.services.digest_service import DigestService
        
        digest_service = DigestService(db)
        
        try:
            digest_data = await digest_service.generate_user_digest(
                user_id=str(user_prefs.user_id),
                period=user_prefs.digest_frequency,
                format_type=user_prefs.digest_format if user_prefs.digest_format else "short"
            )
            
            logger.info(f"✅ Digest generated successfully!")
            logger.info(f"News count: {digest_data['news_count']}")
            logger.info(f"Categories: {list(digest_data['categories'].keys())}")
            
            # Format for Telegram
            digest_text = digest_service.format_digest_for_telegram(digest_data)
            logger.info(f"Telegram message length: {len(digest_text)} characters")
            logger.info(f"Preview: {digest_text[:200]}...")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate digest: {e}")


async def main():
    """Main function"""
    logger.info("🧪 Starting digest scheduler tests...")
    logger.info("=" * 50)
    
    try:
        # Test 1: Check scheduler logic
        logger.info("Test 1: Checking digest scheduler logic...")
        await test_digest_scheduler()
        
        logger.info("\n" + "=" * 50)
        
        # Test 2: Generate test digest
        logger.info("Test 2: Testing digest generation...")
        await test_specific_user_digest()
        
        logger.info("\n✅ All tests completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

