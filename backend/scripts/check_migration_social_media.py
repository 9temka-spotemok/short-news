"""
Script to check if social media migration has been applied.
Checks for:
1. Existence of social media columns in companies table
2. Existence of social media enum values in sourcetype enum
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from app.core.database import get_async_session


async def check_migration():
    """Check if social media migration has been applied"""
    print("🔍 Checking social media migration status...\n")
    
    async for db in get_async_session():
        try:
            # Check 1: Social media columns in companies table
            print("1️⃣ Checking social media columns in 'companies' table...")
            columns_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'companies' 
                AND column_name IN ('facebook_url', 'instagram_url', 'linkedin_url', 'youtube_url', 'tiktok_url')
                ORDER BY column_name;
            """)
            
            result = await db.execute(columns_query)
            found_columns = [row[0] for row in result.fetchall()]
            
            expected_columns = ['facebook_url', 'instagram_url', 'linkedin_url', 'youtube_url', 'tiktok_url']
            missing_columns = [col for col in expected_columns if col not in found_columns]
            
            if missing_columns:
                print(f"   ❌ Missing columns: {', '.join(missing_columns)}")
                print(f"   ✅ Found columns: {', '.join(found_columns)}")
            else:
                print(f"   ✅ All social media columns exist: {', '.join(found_columns)}")
            
            # Check 2: Social media enum values in sourcetype enum
            print("\n2️⃣ Checking social media enum values in 'sourcetype' enum...")
            # Note: PostgreSQL stores enum values in UPPERCASE, but Python uses lowercase
            enum_query = text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'sourcetype')
                AND enumlabel IN ('FACEBOOK', 'INSTAGRAM', 'LINKEDIN', 'YOUTUBE', 'TIKTOK')
                ORDER BY enumlabel;
            """)
            
            result = await db.execute(enum_query)
            found_enums = [row[0] for row in result.fetchall()]
            
            # PostgreSQL stores in UPPERCASE, but we check for both
            expected_enums_upper = ['FACEBOOK', 'INSTAGRAM', 'LINKEDIN', 'YOUTUBE', 'TIKTOK']
            missing_enums = [enum_val for enum_val in expected_enums_upper if enum_val not in found_enums]
            
            if missing_enums:
                print(f"   ❌ Missing enum values: {', '.join(missing_enums)}")
                print(f"   ✅ Found enum values: {', '.join(found_enums)}")
            else:
                print(f"   ✅ All social media enum values exist: {', '.join(found_enums)}")
            
            # Summary
            print("\n" + "="*60)
            if not missing_columns and not missing_enums:
                print("✅ Migration check PASSED: All social media fields are present!")
                return 0
            else:
                print("❌ Migration check FAILED: Some fields are missing!")
                print("\nTo apply migration, run:")
                print("  cd backend && poetry run alembic upgrade head")
                return 1
                
        except Exception as e:
            print(f"❌ Error checking migration: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            await db.close()


if __name__ == "__main__":
    exit_code = asyncio.run(check_migration())
    sys.exit(exit_code)
