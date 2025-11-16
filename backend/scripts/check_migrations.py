#!/usr/bin/env python3
"""
Script to check database migration status and verify required tables exist.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from loguru import logger


async def check_table_exists(session, table_name: str) -> bool:
    """Check if a table exists in the database."""
    try:
        result = await session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                )
                """
            ),
            {"table_name": table_name}
        )
        exists = result.scalar()
        return exists
    except Exception as e:
        logger.error(f"Error checking table {table_name}: {e}")
        return False


async def check_migration_status():
    """Check current migration revision."""
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-m", "alembic", "current"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"
    except Exception as e:
        return f"Error: {str(e)}"


async def check_required_tables():
    """Check if all required tables for notifications exist."""
    required_tables = [
        "notification_channels",
        "notification_events",
        "notification_subscriptions",
        "notification_deliveries",  # This is the one causing the error
    ]
    
    async with AsyncSessionLocal() as session:
        results = {}
        for table in required_tables:
            exists = await check_table_exists(session, table)
            results[table] = exists
            status = "✅" if exists else "❌"
            logger.info(f"{status} Table '{table}': {'exists' if exists else 'MISSING'}")
        
        return results


async def main():
    """Main function."""
    logger.info("Checking database migration status...")
    
    # Check migration status
    migration_status = await check_migration_status()
    logger.info(f"Current migration: {migration_status}")
    
    # Check required tables
    logger.info("\nChecking required tables...")
    table_results = await check_required_tables()
    
    # Summary
    missing_tables = [table for table, exists in table_results.items() if not exists]
    
    if missing_tables:
        logger.error(f"\n❌ Missing tables: {', '.join(missing_tables)}")
        logger.error("Run migrations: python -m alembic upgrade head")
        return 1
    else:
        logger.success("\n✅ All required tables exist!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

