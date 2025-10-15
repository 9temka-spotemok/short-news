#!/usr/bin/env python3
"""
Test script for API endpoint
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.api.v1.endpoints.users import DigestSettingsUpdate
from app.models.preferences import DigestFrequency, DigestFormat


def test_digest_settings_update_model():
    """Test DigestSettingsUpdate model"""
    print("Testing DigestSettingsUpdate model...")
    
    try:
        # Test with all fields
        settings = DigestSettingsUpdate(
            digest_enabled=True,
            digest_frequency="daily",
            digest_format="short",
            digest_include_summaries=True,
            telegram_chat_id="123456789",
            telegram_enabled=True,
            timezone="UTC",
            week_start_day=0
        )
        
        print("OK: DigestSettingsUpdate created successfully")
        print(f"   digest_enabled: {settings.digest_enabled}")
        print(f"   digest_frequency: {settings.digest_frequency}")
        print(f"   digest_format: {settings.digest_format}")
        print(f"   telegram_chat_id: {settings.telegram_chat_id}")
        
        # Test with partial fields
        settings_partial = DigestSettingsUpdate(
            digest_enabled=False,
            telegram_chat_id="987654321"
        )
        
        print("OK: DigestSettingsUpdate with partial fields created successfully")
        print(f"   digest_enabled: {settings_partial.digest_enabled}")
        print(f"   digest_frequency: {settings_partial.digest_frequency}")
        print(f"   telegram_chat_id: {settings_partial.telegram_chat_id}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: DigestSettingsUpdate error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_enum_conversion():
    """Test enum conversion in the endpoint"""
    print("\nTesting enum conversion...")
    
    try:
        # Test DigestFrequency conversion
        freq = DigestFrequency("daily")
        print(f"OK: DigestFrequency('daily') = {freq}")
        
        freq2 = DigestFrequency("weekly")
        print(f"OK: DigestFrequency('weekly') = {freq2}")
        
        # Test DigestFormat conversion
        fmt = DigestFormat("short")
        print(f"OK: DigestFormat('short') = {fmt}")
        
        fmt2 = DigestFormat("detailed")
        print(f"OK: DigestFormat('detailed') = {fmt2}")
        
        # Test invalid values
        try:
            DigestFrequency("invalid")
            print("ERROR: Should have failed for invalid frequency")
        except ValueError:
            print("OK: Correctly rejected invalid frequency")
        
        try:
            DigestFormat("invalid")
            print("ERROR: Should have failed for invalid format")
        except ValueError:
            print("OK: Correctly rejected invalid format")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Enum conversion error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("API Endpoint Testing")
    print("=" * 50)
    
    tests = [
        ("DigestSettingsUpdate Model", test_digest_settings_update_model),
        ("Enum Conversion", test_enum_conversion),
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
        print("All tests passed! The API models are working correctly.")
    else:
        print("Some tests failed. Check the errors above.")


if __name__ == "__main__":
    main()
