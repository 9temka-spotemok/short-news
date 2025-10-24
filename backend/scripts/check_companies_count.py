"""Check companies count in database"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.company import Company

async def check_count():
    async with AsyncSessionLocal() as db:
        count = await db.execute(select(func.count(Company.id)))
        total = count.scalar()
        print(f"Current companies count: {total}")
        return total

if __name__ == "__main__":
    asyncio.run(check_count())
