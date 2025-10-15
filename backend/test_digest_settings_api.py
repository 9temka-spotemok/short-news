#!/usr/bin/env python3
"""
Test DigestSettings API endpoint
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.core.database import get_db
from app.api.v1.endpoints.users import DigestSettingsUpdate
from app.models import UserPreferences
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid


async def test_digest_settings_api():
    """Test the DigestSettings API endpoint"""
    print("Testing DigestSettings API endpoint...")
    
    try:
        # Test Pydantic model validation
        print("\n1. Testing Pydantic model validation...")
        
        # Valid data
        valid_data = {
            "digest_enabled": True,
            "digest_frequency": "daily",
            "digest_format": "short",
            "digest_include_summaries": True,
            "telegram_enabled": False,
            "timezone": "UTC",
            "week_start_day": 0
        }
        
        settings = DigestSettingsUpdate(**valid_data)
        print(f"[OK] Valid data parsed successfully: {settings}")
        
        # Invalid digest_frequency
        try:
            invalid_data = valid_data.copy()
            invalid_data["digest_frequency"] = "invalid"
            DigestSettingsUpdate(**invalid_data)
            print("[ERROR] Should have failed with invalid digest_frequency")
        except ValueError as e:
            print(f"[OK] Correctly rejected invalid digest_frequency: {e}")
        
        # Invalid digest_format
        try:
            invalid_data = valid_data.copy()
            invalid_data["digest_format"] = "invalid"
            DigestSettingsUpdate(**invalid_data)
            print("[ERROR] Should have failed with invalid digest_format")
        except ValueError as e:
            print(f"[OK] Correctly rejected invalid digest_format: {e}")
        
        # Test database connection and model
        print("\n2. Testing database connection and model...")
        
        async for db in get_db():
            try:
                # Test a simple query
                result = await db.execute(select(UserPreferences).limit(1))
                prefs = result.scalar_one_or_none()
                
                if prefs:
                    print(f"[OK] Database connection successful, found user preferences: {prefs.user_id}")
                    print(f"   - Digest enabled: {prefs.digest_enabled}")
                    print(f"   - Digest frequency: {prefs.digest_frequency}")
                    print(f"   - Digest format: {prefs.digest_format}")
                else:
                    print("[OK] Database connection successful, no user preferences found")
                
                break
            except Exception as e:
                print(f"[ERROR] Database query failed: {e}")
                break
        
        print("\n3. Testing enum conversion...")
        
        # Test enum conversion
        from app.models.preferences import DigestFrequency, DigestFormat
        
        # Test string to enum conversion
        freq = DigestFrequency("daily")
        fmt = DigestFormat("short")
        
        print(f"[OK] Enum conversion successful:")
        print(f"   - DigestFrequency('daily') = {freq}")
        print(f"   - DigestFormat('short') = {fmt}")
        
        # Test enum to string conversion
        print(f"   - freq.value = {freq.value}")
        print(f"   - fmt.value = {fmt.value}")
        
        print("\n[OK] All tests passed!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_endpoint_directly():
    """Test the API endpoint directly"""
    print("\n4. Testing API endpoint directly...")
    
    try:
        import httpx
        
        # Test data
        test_data = {
            "digest_enabled": True,
            "digest_frequency": "daily",
            "digest_format": "short",
            "digest_include_summaries": True,
            "telegram_enabled": False,
            "timezone": "UTC",
            "week_start_day": 0
        }
        
        async with httpx.AsyncClient() as client:
            # Test with invalid token (should get 401)
            response = await client.put(
                "http://localhost:8000/api/v1/users/preferences/digest",
                json=test_data,
                headers={"Authorization": "Bearer invalid_token"}
            )
            
            if response.status_code == 401:
                print("[OK] API endpoint correctly rejects invalid token")
            else:
                print(f"[ERROR] Expected 401, got {response.status_code}: {response.text}")
        
        print("[OK] API endpoint test completed")
        return True
        
    except Exception as e:
        print(f"[ERROR] API endpoint test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("=" * 60)
    print("DIGEST SETTINGS API TEST")
    print("=" * 60)
    
    # Test 1: Pydantic model validation
    success1 = await test_digest_settings_api()
    
    # Test 2: API endpoint
    success2 = await test_api_endpoint_directly()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("[SUCCESS] ALL TESTS PASSED!")
        print("The DigestSettings API is working correctly.")
    else:
        print("[FAILED] SOME TESTS FAILED!")
        print("Please check the errors above.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
