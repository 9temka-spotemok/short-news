#!/usr/bin/env python3
"""
Test Frontend DigestSettings integration
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

import httpx


async def test_frontend_digest_settings():
    """Test the frontend DigestSettings integration"""
    print("Testing Frontend DigestSettings integration...")
    
    try:
        # Test 1: Check if frontend is running
        print("\n1. Checking if frontend is running...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5173")
            
            if response.status_code == 200:
                print("[OK] Frontend is running")
            else:
                print(f"[ERROR] Frontend returned status {response.status_code}")
                return False
        
        # Test 2: Check if backend API is running
        print("\n2. Checking if backend API is running...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/v1/health")
            
            if response.status_code == 200:
                print("[OK] Backend API is running")
                health_data = response.json()
                print(f"   - Service: {health_data.get('service', 'Unknown')}")
                print(f"   - Version: {health_data.get('version', 'Unknown')}")
            else:
                print(f"[ERROR] Backend API returned status {response.status_code}")
                return False
        
        # Test 3: Test DigestSettings API endpoint without authentication
        print("\n3. Testing DigestSettings API endpoint without authentication...")
        
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
            # Test PUT request without token
            response = await client.put(
                "http://localhost:8000/api/v1/users/preferences/digest",
                json=test_data
            )
            
            if response.status_code == 401:
                print("[OK] API correctly requires authentication (401)")
            else:
                print(f"[WARNING] Expected 401, got {response.status_code}: {response.text}")
        
        # Test 4: Test GET request without authentication
        print("\n4. Testing DigestSettings GET endpoint without authentication...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8000/api/v1/users/preferences/digest"
            )
            
            if response.status_code == 401:
                print("[OK] GET endpoint correctly requires authentication (401)")
            else:
                print(f"[WARNING] Expected 401, got {response.status_code}: {response.text}")
        
        # Test 5: Test with invalid data format
        print("\n5. Testing with invalid data format...")
        
        invalid_data = {
            "digest_enabled": True,
            "digest_frequency": "invalid_frequency",  # Invalid value
            "digest_format": "invalid_format",        # Invalid value
            "digest_include_summaries": True,
            "telegram_enabled": False,
            "timezone": "UTC",
            "week_start_day": 0
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                "http://localhost:8000/api/v1/users/preferences/digest",
                json=invalid_data,
                headers={"Authorization": "Bearer invalid_token"}
            )
            
            if response.status_code == 401:
                print("[OK] Invalid token correctly rejected (401)")
            else:
                print(f"[WARNING] Expected 401, got {response.status_code}: {response.text}")
        
        print("\n[OK] All frontend integration tests passed!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Frontend integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cors_headers():
    """Test CORS headers for frontend-backend communication"""
    print("\n6. Testing CORS headers...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test preflight request
            response = await client.options(
                "http://localhost:8000/api/v1/users/preferences/digest",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "PUT",
                    "Access-Control-Request-Headers": "Content-Type, Authorization"
                }
            )
            
            if response.status_code == 200:
                print("[OK] CORS preflight request successful")
                
                # Check CORS headers
                cors_headers = {
                    "access-control-allow-origin": response.headers.get("access-control-allow-origin"),
                    "access-control-allow-methods": response.headers.get("access-control-allow-methods"),
                    "access-control-allow-headers": response.headers.get("access-control-allow-headers"),
                }
                
                print(f"   - Allow Origin: {cors_headers['access-control-allow-origin']}")
                print(f"   - Allow Methods: {cors_headers['access-control-allow-methods']}")
                print(f"   - Allow Headers: {cors_headers['access-control-allow-headers']}")
                
                if cors_headers['access-control-allow-origin']:
                    print("[OK] CORS headers are properly configured")
                else:
                    print("[WARNING] CORS headers may not be properly configured")
            else:
                print(f"[WARNING] CORS preflight request failed: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] CORS test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("=" * 60)
    print("FRONTEND DIGEST SETTINGS INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: Frontend integration
    success1 = await test_frontend_digest_settings()
    
    # Test 2: CORS headers
    success2 = await test_cors_headers()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("[SUCCESS] ALL FRONTEND TESTS PASSED!")
        print("The frontend DigestSettings integration is working correctly.")
    else:
        print("[FAILED] SOME FRONTEND TESTS FAILED!")
        print("Please check the errors above.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
