"""
Database configuration and session management
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from loguru import logger

from app.core.config import settings


# Create async engine
# Note: asyncpg is an async-only driver
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """
    Dependency to get database session
    """
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db():
    """
    Initialize database connection
    """
    try:
        # Test connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error(f"Database URL format: {settings.DATABASE_URL[:50]}...")
        
        # Provide more specific error information
        if "password authentication failed" in str(e):
            logger.error("Password authentication failed - check database credentials")
        elif "connection refused" in str(e):
            logger.error("Connection refused - check database host and port")
        elif "database" in str(e) and "does not exist" in str(e):
            logger.error("Database does not exist - check database name")
        
        raise


async def get_async_session():
    """
    Generator function to get database session for scripts
    Similar to get_db() but can be used in async for loops
    """
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


async def close_db():
    """
    Close database connections
    """
    await engine.dispose()
    logger.info("Database connections closed")
