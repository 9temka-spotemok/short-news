#!/usr/bin/env python3
"""
Fix missing UserPreferences for existing users
This script creates UserPreferences for users who don't have them
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from loguru import logger
import uuid

from app.core.database import AsyncSessionLocal
from app.models import User, UserPreferences


async def fix_missing_user_preferences():
    """Create UserPreferences for users who don't have them"""
    
    async with AsyncSessionLocal() as db:
        # Get all users
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        logger.info(f"Found {len(users)} users")
        
        fixed_count = 0
        for user in users:
            # Check if user has preferences
            result = await db.execute(
                select(UserPreferences).where(UserPreferences.user_id == user.id)
            )
            existing_prefs = result.scalar_one_or_none()
            
            if not existing_prefs:
                # Create default preferences
                prefs = UserPreferences(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    subscribed_companies=[],
                    interested_categories=[],
                    keywords=[],
                    notification_frequency='daily',
                    digest_enabled=False,  # Disabled by default
                    digest_frequency='daily',
                    digest_custom_schedule={},
                    digest_format='short',
                    digest_include_summaries=True,
                    telegram_chat_id=None,
                    telegram_enabled=False,  # Disabled by default
                    timezone='UTC',
                    week_start_day=0
                )
                
                db.add(prefs)
                fixed_count += 1
                logger.info(f"Created preferences for user {user.email}")
        
        await db.commit()
        logger.info(f"Fixed {fixed_count} users with missing preferences")
        
        return fixed_count


async def main():
    """Main function"""
    logger.info("Starting UserPreferences fix...")
    
    try:
        fixed_count = await fix_missing_user_preferences()
        
        if fixed_count > 0:
            logger.success(f"✅ Successfully fixed {fixed_count} users")
            logger.info("Now new users will automatically get UserPreferences created during registration")
            logger.info("Existing users without preferences have been fixed")
        else:
            logger.info("✅ All users already have UserPreferences")
            
    except Exception as e:
        logger.error(f"❌ Error fixing UserPreferences: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())































