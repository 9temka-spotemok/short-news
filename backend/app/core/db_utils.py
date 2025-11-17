"""
Database utility functions for checking column and table existence.
"""

from typing import Optional
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger


async def column_exists(session: AsyncSession, table_name: str, column_name: str) -> bool:
    """
    Check if a column exists in a table.
    
    Args:
        session: Database session
        table_name: Name of the table
        column_name: Name of the column
        
    Returns:
        True if column exists, False otherwise
    """
    try:
        result = await session.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name 
                    AND column_name = :column_name
                )
            """),
            {"table_name": table_name, "column_name": column_name}
        )
        exists = result.scalar()
        return bool(exists)
    except Exception as e:
        logger.error(f"Error checking column {table_name}.{column_name}: {e}")
        return False


async def table_exists(session: AsyncSession, table_name: str) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        session: Database session
        table_name: Name of the table
        
    Returns:
        True if table exists, False otherwise
    """
    try:
        result = await session.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                )
            """),
            {"table_name": table_name}
        )
        exists = result.scalar()
        return bool(exists)
    except Exception as e:
        logger.error(f"Error checking table {table_name}: {e}")
        return False

