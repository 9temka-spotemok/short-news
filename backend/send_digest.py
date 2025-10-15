#!/usr/bin/env python3
"""
Send digest to Telegram
"""

from celery_app import celery_app
from app.tasks.digest import generate_user_digest

if __name__ == "__main__":
    print("🚀 Sending digest to Telegram...")
    
    # Send weekly digest to user
    task = generate_user_digest.delay('7e0556e1-2b75-43ff-b604-d09b767da3ad', 'weekly')
    
    print(f"Task ID: {task.id}")
    print("✅ Digest sent to Telegram!")
