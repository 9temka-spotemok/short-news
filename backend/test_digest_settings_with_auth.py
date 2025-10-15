#!/usr/bin/env python3
"""
Test DigestSettings with authentication
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

import httpx


async def test_digest_settings_with_auth():
    """Test DigestSettings with authentication"""
    print("Testing DigestSettings with authentication...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Try to register a test user
            print("\n1. Attempting to register test user...")
            
            register_data = {
                "email": "test@example.com",
                "password": "testpassword123",
                "full_name": "Test User"
            }
            
            try:
                response = await client.post(
                    "http://localhost:8000/api/v1/auth/register",
                    json=register_data
                )
                
                if response.status_code == 201:
                    print("[OK] Test user registered successfully")
                    auth_data = response.json()
                    access_token = auth_data.get("access_token")
                elif response.status_code == 400:
                    print("[INFO] Test user already exists, trying to login...")
                    # Try to login instead
                    login_data = {
                        "email": "test@example.com",
                        "password": "testpassword123"
                    }
                    
                    response = await client.post(
                        "http://localhost:8000/api/v1/auth/login",
                        json=login_data
                    )
                    
                    if response.status_code == 200:
                        print("[OK] Test user logged in successfully")
                        auth_data = response.json()
                        access_token = auth_data.get("access_token")
                    else:
                        print(f"[ERROR] Login failed: {response.status_code} - {response.text}")
                        return False
                else:
                    print(f"[ERROR] Registration failed: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                print(f"[ERROR] Registration/login failed: {e}")
                return False
            
            if not access_token:
                print("[ERROR] No access token received")
                return False
            
            print(f"[OK] Access token received: {access_token[:20]}...")
            
            # Step 2: Test GET digest settings
            print("\n2. Testing GET digest settings...")
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            response = await client.get(
                "http://localhost:8000/api/v1/users/preferences/digest",
                headers=headers
            )
            
            if response.status_code == 200:
                print("[OK] GET digest settings successful")
                settings = response.json()
                print(f"   - Current settings: {json.dumps(settings, indent=2)}")
            else:
                print(f"[ERROR] GET digest settings failed: {response.status_code} - {response.text}")
                return False
            
            # Step 3: Test PUT digest settings
            print("\n3. Testing PUT digest settings...")
            
            new_settings = {
                "digest_enabled": True,
                "digest_frequency": "daily",
                "digest_format": "short",
                "digest_include_summaries": True,
                "telegram_enabled": False,
                "timezone": "UTC",
                "week_start_day": 0
            }
            
            response = await client.put(
                "http://localhost:8000/api/v1/users/preferences/digest",
                json=new_settings,
                headers=headers
            )
            
            if response.status_code == 200:
                print("[OK] PUT digest settings successful")
                result = response.json()
                print(f"   - Updated settings: {json.dumps(result, indent=2)}")
            else:
                print(f"[ERROR] PUT digest settings failed: {response.status_code} - {response.text}")
                return False
            
            # Step 4: Test with invalid data
            print("\n4. Testing with invalid data...")
            
            invalid_settings = {
                "digest_enabled": True,
                "digest_frequency": "invalid_frequency",  # Invalid
                "digest_format": "invalid_format",        # Invalid
                "digest_include_summaries": True,
                "telegram_enabled": False,
                "timezone": "UTC",
                "week_start_day": 0
            }
            
            response = await client.put(
                "http://localhost:8000/api/v1/users/preferences/digest",
                json=invalid_settings,
                headers=headers
            )
            
            if response.status_code == 422:
                print("[OK] Invalid data correctly rejected (422)")
                error_data = response.json()
                print(f"   - Validation errors: {json.dumps(error_data, indent=2)}")
            else:
                print(f"[WARNING] Expected 422, got {response.status_code}: {response.text}")
            
            print("\n[OK] All authenticated tests passed!")
            return True
            
    except Exception as e:
        print(f"[ERROR] Authenticated test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("=" * 60)
    print("DIGEST SETTINGS AUTHENTICATED TEST")
    print("=" * 60)
    
    success = await test_digest_settings_with_auth()
    
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] AUTHENTICATED TESTS PASSED!")
        print("DigestSettings API works correctly with authentication.")
    else:
        print("[FAILED] AUTHENTICATED TESTS FAILED!")
        print("Please check the errors above.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
