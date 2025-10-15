"""
Initialize all user settings (preferences + notifications)
Run this after migration to ensure all users have default settings
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from init_user_preferences import init_user_preferences
from init_notification_settings import init_notification_settings
from loguru import logger


async def main():
    """Initialize all settings"""
    logger.info("=== Starting initialization of all user settings ===")
    
    # Initialize user preferences
    logger.info("\n1. Initializing user preferences...")
    prefs_count = await init_user_preferences()
    
    # Initialize notification settings
    logger.info("\n2. Initializing notification settings...")
    notif_count = await init_notification_settings()
    
    logger.info("\n=== Initialization complete ===")
    logger.info(f"Created {prefs_count} user preferences")
    logger.info(f"Created {notif_count} notification settings")
    
    return prefs_count, notif_count


if __name__ == "__main__":
    asyncio.run(main())



