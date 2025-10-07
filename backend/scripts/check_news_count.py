"""Check news count in database"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.news import NewsItem

async def check_count():
    async with AsyncSessionLocal() as db:
        count = await db.execute(select(func.count(NewsItem.id)))
        total = count.scalar()
        print(f"Current news count: {total}")
        return total

if __name__ == "__main__":
    asyncio.run(check_count())

