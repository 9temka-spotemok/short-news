#!/usr/bin/env python3
"""
Test database connection
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.config import settings


async def test_db_connection():
    """Test database connection"""
    print("Testing database connection...")
    
    try:
        print(f"Database URL: {settings.DATABASE_URL}")
        
        # Try to import and test database
        from app.core.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            # Simple query to test connection
            from sqlalchemy import text
            result = await db.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                print("OK: Database connection successful")
                return True
            else:
                print("ERROR: Database query failed")
                return False
                
    except Exception as e:
        print(f"ERROR: Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_db_connection()
    
    if success:
        print("\nDatabase connection test PASSED")
    else:
        print("\nDatabase connection test FAILED")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())
