"""
Create demo user for the application
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from loguru import logger

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash


async def create_demo_user():
    """Create demo user"""
    logger.info("Creating demo user...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if demo user already exists
            result = await db.execute(
                select(User).where(User.email == "demo@shot-news.com")
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info("Demo user already exists")
                return {"status": "exists", "email": "demo@shot-news.com"}
            
            # Create demo user
            demo_user = User(
                email="demo@shot-news.com",
                password_hash=get_password_hash("demo123"),
                full_name="Demo User",
                is_active=True,
                is_verified=True
            )
            
            db.add(demo_user)
            await db.commit()
            
            logger.info("✅ Demo user created successfully!")
            logger.info(f"   Email: demo@shot-news.com")
            logger.info(f"   Password: demo123")
            
            return {"status": "created", "email": "demo@shot-news.com"}
            
        except Exception as e:
            logger.error(f"Failed to create demo user: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    result = asyncio.run(create_demo_user())
    print(f"\nDemo user: {result['email']}")
    print(f"Status: {result['status']}")



