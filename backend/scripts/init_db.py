#!/usr/bin/env python3
"""
Database initialization script for Docker containers
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path
import asyncpg
from loguru import logger

async def wait_for_database(max_retries: int = 30, retry_delay: int = 2):
    """Wait for database to be ready"""
    logger.info("Waiting for database to be ready...")
    
    for attempt in range(max_retries):
        try:
            conn = await asyncpg.connect(os.environ['DATABASE_URL'])
            await conn.close()
            logger.info("Database is ready!")
            return True
        except Exception as e:
            logger.warning(f"Database not ready (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Database failed to become ready after maximum retries")
                return False
    
    return False

def apply_migrations():
    """Apply database migrations"""
    logger.info("Applying database migrations...")
    
    try:
        result = subprocess.run(
            ["python", "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd="/app"
        )
        
        if result.returncode == 0:
            logger.info("Migrations applied successfully!")
            if result.stdout:
                logger.info(f"Migration output: {result.stdout}")
            return True
        else:
            logger.error(f"Migration failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")
        return False

def check_migration_status():
    """Check current migration status"""
    logger.info("Checking migration status...")
    
    try:
        result = subprocess.run(
            ["python", "-m", "alembic", "current"],
            capture_output=True,
            text=True,
            cwd="/app"
        )
        
        if result.returncode == 0:
            logger.info(f"Current migration: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"Failed to check migration status: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        return False

async def initialize_database():
    """Initialize database with migrations"""
    logger.info("Starting database initialization...")
    
    # Wait for database
    if not await wait_for_database():
        logger.error("Failed to connect to database")
        return False
    
    # Apply migrations
    if not apply_migrations():
        logger.error("Failed to apply migrations")
        return False
    
    # Check status
    if not check_migration_status():
        logger.error("Failed to check migration status")
        return False
    
    logger.info("Database initialization completed successfully!")
    return True

if __name__ == "__main__":
    # Check if we're in Docker
    if os.path.exists("/.dockerenv"):
        logger.info("Running in Docker container")
    
    # Run initialization
    success = asyncio.run(initialize_database())
    
    if not success:
        logger.error("Database initialization failed!")
        sys.exit(1)
    
    logger.info("Database initialization completed!")
    sys.exit(0)
