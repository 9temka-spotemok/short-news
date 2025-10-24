"""Check news categories distribution"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.news import NewsItem

async def check_categories():
    async with AsyncSessionLocal() as db:
        # Get category distribution
        result = await db.execute(
            select(NewsItem.category, func.count(NewsItem.id).label('count'))
            .where(NewsItem.category.isnot(None))
            .group_by(NewsItem.category)
            .order_by(func.count(NewsItem.id).desc())
        )
        
        print("News categories distribution:")
        for category, count in result.all():
            print(f"  {category}: {count}")
        
        # Get total news count
        total_result = await db.execute(select(func.count(NewsItem.id)))
        total = total_result.scalar()
        print(f"\nTotal news items: {total}")

if __name__ == "__main__":
    asyncio.run(check_categories())
