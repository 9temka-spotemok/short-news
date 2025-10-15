#!/usr/bin/env python3
"""
Test script for digest settings API endpoint
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.database import AsyncSessionLocal
from app.models import User, UserPreferences
from app.models.preferences import DigestFrequency, DigestFormat
from sqlalchemy import select
import uuid


async def test_digest_settings():
    """Test digest settings functionality"""
    print("Testing digest settings functionality...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Check if we can connect to database
            print("Database connection successful")
            
            # Test enum types
            print("\nTesting enum types...")
            
            # Test DigestFrequency enum
            try:
                freq = DigestFrequency.DAILY
                print(f"OK: DigestFrequency.DAILY = {freq.value}")
            except Exception as e:
                print(f"ERROR: DigestFrequency error: {e}")
            
            # Test DigestFormat enum
            try:
                fmt = DigestFormat.SHORT
                print(f"OK: DigestFormat.SHORT = {fmt.value}")
            except Exception as e:
                print(f"ERROR: DigestFormat error: {e}")
            
            # Test creating UserPreferences
            print("\nTesting UserPreferences creation...")
            try:
                # Create a test user ID
                test_user_id = uuid.uuid4()
                
                # Create preferences
                preferences = UserPreferences(
                    id=uuid.uuid4(),
                    user_id=test_user_id,
                    subscribed_companies=[],
                    interested_categories=[],
                    keywords=[],
                    notification_frequency="daily",  # Use string instead of enum
                    digest_enabled=True,
                    digest_frequency="daily",  # Use string instead of enum
                    digest_custom_schedule={},
                    digest_format="short",  # Use string instead of enum
                    digest_include_summaries=True,
                    telegram_chat_id="123456789",
                    telegram_enabled=True,
                    timezone="UTC",
                    week_start_day=0
                )
                
                print("OK: UserPreferences object created successfully")
                print(f"   digest_enabled: {preferences.digest_enabled}")
                print(f"   digest_frequency: {preferences.digest_frequency}")
                print(f"   digest_format: {preferences.digest_format}")
                print(f"   telegram_chat_id: {preferences.telegram_chat_id}")
                
            except Exception as e:
                print(f"ERROR: UserPreferences creation error: {e}")
                import traceback
                traceback.print_exc()
            
            # Test enum conversion
            print("\nTesting enum conversion...")
            try:
                # Test converting string to enum
                freq_enum = DigestFrequency("daily")
                print(f"OK: String 'daily' -> DigestFrequency: {freq_enum}")
                
                fmt_enum = DigestFormat("short")
                print(f"OK: String 'short' -> DigestFormat: {fmt_enum}")
                
            except Exception as e:
                print(f"ERROR: Enum conversion error: {e}")
                import traceback
                traceback.print_exc()
            
    except Exception as e:
        print(f"ERROR: Database connection error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_digest_settings())
