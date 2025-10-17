#!/usr/bin/env python3
"""
Test digest generation via Docker container
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.tasks.digest import generate_user_digest

def test_digest_generation():
    """Test digest generation"""
    
    # Test user ID from logs
    user_id = "7e0556e1-2b75-43ff-b604-d09b767da3ad"
    
    print(f"Testing digest generation for user: {user_id}")
    
    # Run the task synchronously
    result = generate_user_digest.delay(user_id, "daily")
    
    print(f"Task ID: {result.id}")
    print(f"Task status: {result.status}")
    
    # Wait for result
    try:
        task_result = result.get(timeout=30)
        print(f"Task result: {task_result}")
    except Exception as e:
        print(f"Task failed: {e}")

if __name__ == "__main__":
    test_digest_generation()
