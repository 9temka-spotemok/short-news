#!/usr/bin/env python3
"""
Simple database connection checker for Docker containers
"""

import asyncio
import sys
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def check_database():
    """Check if database is ready"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text('SELECT 1'))
            row = result.fetchone()
            if row:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection failed: No result")
                return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(check_database())
    sys.exit(0 if success else 1)
