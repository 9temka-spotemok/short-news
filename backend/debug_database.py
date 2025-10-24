#!/usr/bin/env python3
"""
Database connection debug script for Railway deployment
This script helps diagnose database connection issues
"""

import os
import sys
import asyncio
import asyncpg
from urllib.parse import urlparse
from loguru import logger

def parse_database_url(url):
    """Parse database URL and return connection parameters"""
    try:
        parsed = urlparse(url)
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'user': parsed.username,
            'password': parsed.password,
            'database': parsed.path[1:] if parsed.path else 'postgres',
            'scheme': parsed.scheme
        }
    except Exception as e:
        logger.error(f"Failed to parse database URL: {e}")
        return None

async def test_database_connection():
    """Test database connection with detailed error reporting"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable is not set")
        return False
    
    logger.info("Testing database connection...")
    logger.info(f"Database URL: {database_url[:50]}...")
    
    # Parse URL
    db_params = parse_database_url(database_url)
    if not db_params:
        return False
    
    logger.info(f"Parsed connection parameters:")
    logger.info(f"  Host: {db_params['host']}")
    logger.info(f"  Port: {db_params['port']}")
    logger.info(f"  User: {db_params['user']}")
    logger.info(f"  Password: {'***' if db_params['password'] else 'None'}")
    logger.info(f"  Database: {db_params['database']}")
    
    # Test connection
    try:
        conn = await asyncpg.connect(
            host=db_params['host'],
            port=db_params['port'],
            user=db_params['user'],
            password=db_params['password'],
            database=db_params['database']
        )
        
        # Test query
        result = await conn.fetchval('SELECT 1')
        logger.info(f"Database connection successful! Test query result: {result}")
        
        # Get database info
        version = await conn.fetchval('SELECT version()')
        logger.info(f"PostgreSQL version: {version}")
        
        await conn.close()
        return True
        
    except asyncpg.exceptions.InvalidPasswordError as e:
        logger.error(f"Password authentication failed: {e}")
        logger.error("Check if the password in DATABASE_URL is correct")
        return False
        
    except asyncpg.exceptions.InvalidAuthorizationSpecificationError as e:
        logger.error(f"Authorization failed: {e}")
        logger.error("Check if the user exists and has proper permissions")
        return False
        
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        logger.error(f"Database does not exist: {e}")
        logger.error("Check if the database name in DATABASE_URL is correct")
        return False
        
    except asyncpg.exceptions.ConnectionRefusedError as e:
        logger.error(f"Connection refused: {e}")
        logger.error("Check if the database host and port are correct")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        return False

async def main():
    """Main function"""
    logger.info("=== Database Connection Debug ===")
    
    # Check environment variables
    required_vars = ['DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Make sure these are set in Railway dashboard")
        return False
    
    # Test database connection
    success = await test_database_connection()
    
    if success:
        logger.info("✅ Database connection test passed!")
        return True
    else:
        logger.error("❌ Database connection test failed!")
        logger.error("Please check your Railway database configuration")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
