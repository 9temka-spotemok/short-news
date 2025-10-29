"""Script to check ENUM values in Railway database"""

import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def check_enums():
    async with AsyncSessionLocal() as session:
        # Check sourcetype enum
        result = await session.execute(
            text("SELECT enumlabel FROM pg_enum WHERE enumtypid = 'sourcetype'::regtype ORDER BY enumsortorder")
        )
        sourcetype_values = [r[0] for r in result]
        print("sourcetype values:", sourcetype_values)
        
        # Check newscategory enum  
        result = await session.execute(
            text("SELECT enumlabel FROM pg_enum WHERE enumtypid = 'newscategory'::regtype ORDER BY enumsortorder")
        )
        newscategory_values = [r[0] for r in result]
        print("newscategory values:", newscategory_values)
        
        # Check some actual news items
        result = await session.execute(
            text("SELECT DISTINCT source_type FROM news_items LIMIT 10")
        )
        source_types_in_use = [r[0] for r in result]
        print("source_type values in news_items:", source_types_in_use)
        
        result = await session.execute(
            text("SELECT DISTINCT category FROM news_items LIMIT 10")
        )
        categories_in_use = [r[0] for r in result]
        print("category values in news_items:", categories_in_use)

if __name__ == "__main__":
    asyncio.run(check_enums())

