"""
Initialize user preferences for all users without them
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from loguru import logger
import uuid

from app.core.database import AsyncSessionLocal
from app.models import User, UserPreferences
from app.models.preferences import NotificationFrequency, DigestFrequency, DigestFormat


async def init_user_preferences():
    """Create default preferences for users who don't have them"""
    
    async with AsyncSessionLocal() as db:
        # Get all users
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        logger.info(f"Found {len(users)} users")
        
        created_count = 0
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
                    notification_frequency=NotificationFrequency.DAILY,
                    digest_enabled=False,
                    digest_frequency=DigestFrequency.DAILY,
                    digest_custom_schedule={},
                    digest_format=DigestFormat.SHORT,
                    digest_include_summaries=True,
                    telegram_chat_id=None,
                    telegram_enabled=False
                )
                
                db.add(prefs)
                created_count += 1
                logger.info(f"Created preferences for user {user.email}")
        
        await db.commit()
        logger.info(f"Created {created_count} user preferences")
        
        return created_count


if __name__ == "__main__":
    logger.info("Starting user preferences initialization")
    count = asyncio.run(init_user_preferences())
    logger.info(f"Completed! Created {count} preferences")

