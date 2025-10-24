"""Check specific business intelligence categories"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.news import NewsItem

async def check_business_categories():
    async with AsyncSessionLocal() as db:
        # Categories we're looking for in Business Intelligence
        business_categories = [
            'funding_news',
            'partnership', 
            'acquisition',
            'strategic_announcement',
            'integration'
        ]
        
        print("Business Intelligence categories:")
        for category in business_categories:
            result = await db.execute(
                select(func.count(NewsItem.id))
                .where(NewsItem.category == category)
            )
            count = result.scalar()
            print(f"  {category}: {count}")
        
        # Check if there are any news with these categories for a specific company
        print("\nChecking for companies with business intelligence data...")
        
        # Get a sample company
        result = await db.execute(
            select(NewsItem.company_id, func.count(NewsItem.id).label('count'))
            .where(NewsItem.category.in_(business_categories))
            .group_by(NewsItem.company_id)
            .order_by(func.count(NewsItem.id).desc())
            .limit(5)
        )
        
        print("Top companies with business intelligence news:")
        for company_id, count in result.all():
            print(f"  Company {company_id}: {count} business news")

if __name__ == "__main__":
    asyncio.run(check_business_categories())
