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


async def ensure_news_items_columns(session: AsyncSession) -> bool:
    """
    Ensure that news_items table has all required columns.
    This is a fallback mechanism in case migrations failed to apply.
    
    Args:
        session: Database session
        
    Returns:
        True if all columns exist or were successfully added, False otherwise
    """
    try:
        # Check and create enum types if needed
        enum_queries = [
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'newstopic') THEN
                    CREATE TYPE newstopic AS ENUM (
                        'product', 'strategy', 'finance', 'technology', 'security',
                        'research', 'community', 'talent', 'regulation', 'market', 'other'
                    );
                END IF;
            END $$;
            """,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sentimentlabel') THEN
                    CREATE TYPE sentimentlabel AS ENUM (
                        'positive', 'neutral', 'negative', 'mixed'
                    );
                END IF;
            END $$;
            """
        ]
        
        for query in enum_queries:
            try:
                await session.execute(text(query))
                await session.commit()
            except Exception as e:
                logger.warning(f"Error creating enum type (may already exist): {e}")
                await session.rollback()
        
        # Check and add columns
        columns_to_add = [
            ("topic", "newstopic", "NULL"),
            ("sentiment", "sentimentlabel", "NULL"),
            ("raw_snapshot_url", "VARCHAR(1000)", "NULL"),
        ]
        
        added_columns = []
        for column_name, column_type, default in columns_to_add:
            exists = await column_exists(session, "news_items", column_name)
            if not exists:
                try:
                    await session.execute(
                        text(f"""
                            ALTER TABLE news_items 
                            ADD COLUMN {column_name} {column_type} DEFAULT {default}
                        """)
                    )
                    await session.commit()
                    added_columns.append(column_name)
                    logger.info(f"Added missing column news_items.{column_name}")
                except Exception as e:
                    logger.error(f"Failed to add column news_items.{column_name}: {e}")
                    await session.rollback()
                    return False
        
        if added_columns:
            logger.info(f"Successfully added columns to news_items: {', '.join(added_columns)}")
        else:
            logger.debug("All required columns exist in news_items table")
        
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring news_items columns: {e}")
        await session.rollback()
        return False

