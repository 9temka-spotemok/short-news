"""
Initialize notification settings for all users without them
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
from app.models import User, NotificationSettings


async def init_notification_settings():
    """Create default notification settings for users who don't have them"""
    
    async with AsyncSessionLocal() as db:
        # Get all users
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        logger.info(f"Found {len(users)} users")
        
        created_count = 0
        for user in users:
            # Check if user has notification settings
            result = await db.execute(
                select(NotificationSettings).where(NotificationSettings.user_id == user.id)
            )
            existing_settings = result.scalar_one_or_none()
            
            if not existing_settings:
                # Create default settings
                settings = NotificationSettings(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    enabled=True,
                    notification_types={},  # Empty = all enabled by default
                    min_priority_score=0,
                    company_alerts=True,
                    category_trends=True,
                    keyword_alerts=True
                )
                
                db.add(settings)
                created_count += 1
                logger.info(f"Created notification settings for user {user.email}")
        
        await db.commit()
        logger.info(f"Created {created_count} notification settings")
        
        return created_count


if __name__ == "__main__":
    logger.info("Starting notification settings initialization")
    count = asyncio.run(init_notification_settings())
    logger.info(f"Completed! Created {count} notification settings")



