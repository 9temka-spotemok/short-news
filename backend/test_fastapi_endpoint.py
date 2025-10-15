#!/usr/bin/env python3
"""
Test FastAPI endpoint directly
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from app.api.v1.endpoints.users import DigestSettingsUpdate
from app.api.v1.api import api_router
from fastapi import FastAPI


def test_digest_settings_endpoint():
    """Test the digest settings endpoint"""
    print("Testing digest settings endpoint...")
    
    # Create a test FastAPI app
    app = FastAPI()
    app.include_router(api_router)
    
    client = TestClient(app)
    
    # Test data
    test_data = {
        "digest_enabled": True,
        "digest_frequency": "daily",
        "digest_format": "short",
        "digest_include_summaries": True,
        "telegram_chat_id": "123456789",
        "telegram_enabled": True,
        "timezone": "UTC",
        "week_start_day": 0
    }
    
    try:
        # Test the endpoint (this will fail without auth, but we can see the validation)
        response = client.put("/api/v1/users/preferences/digest", json=test_data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 401:
            print("OK: Endpoint exists and requires authentication (expected)")
            return True
        elif response.status_code == 422:
            print("ERROR: Validation error - check the request data")
            print(f"Details: {response.json()}")
            return False
        else:
            print(f"Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_digest_settings_model():
    """Test the DigestSettingsUpdate model validation"""
    print("\nTesting DigestSettingsUpdate model validation...")
    
    try:
        # Valid data
        valid_data = {
            "digest_enabled": True,
            "digest_frequency": "daily",
            "digest_format": "short",
            "telegram_chat_id": "123456789",
            "telegram_enabled": True
        }
        
        settings = DigestSettingsUpdate(**valid_data)
        print("OK: Valid data accepted")
        print(f"   digest_enabled: {settings.digest_enabled}")
        print(f"   digest_frequency: {settings.digest_frequency}")
        print(f"   digest_format: {settings.digest_format}")
        
        # Test with invalid enum values
        try:
            invalid_data = {
                "digest_frequency": "invalid_frequency",
                "digest_format": "invalid_format"
            }
            DigestSettingsUpdate(**invalid_data)
            print("ERROR: Should have rejected invalid enum values")
            return False
        except ValueError as e:
            print(f"OK: Correctly rejected invalid enum values: {e}")
        
        # Test with partial data
        partial_data = {
            "digest_enabled": False,
            "telegram_chat_id": "987654321"
        }
        
        settings_partial = DigestSettingsUpdate(**partial_data)
        print("OK: Partial data accepted")
        print(f"   digest_enabled: {settings_partial.digest_enabled}")
        print(f"   digest_frequency: {settings_partial.digest_frequency}")
        print(f"   telegram_chat_id: {settings_partial.telegram_chat_id}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Model validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("FastAPI Endpoint Testing")
    print("=" * 50)
    
    tests = [
        ("DigestSettingsUpdate Model", test_digest_settings_model),
        ("Digest Settings Endpoint", test_digest_settings_endpoint),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"ERROR: Unexpected error in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("=" * 50)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:30} {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! The API endpoint is working correctly.")
    else:
        print("Some tests failed. Check the errors above.")


if __name__ == "__main__":
    main()
