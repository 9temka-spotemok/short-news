"""Check users in database"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.user import User

async def check_users():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count(User.id)))
        total = result.scalar()
        print(f"Total users: {total}")
        
        if total > 0:
            # Get first user
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            if user:
                print(f"First user: {user.email}")

if __name__ == "__main__":
    asyncio.run(check_users())
