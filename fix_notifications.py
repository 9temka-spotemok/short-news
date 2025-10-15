"""
Quick fix script for notification errors
Run this from project root: python fix_notifications.py
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models import User, UserPreferences, NotificationSettings, Notification
from app.models.preferences import NotificationFrequency, DigestFrequency, DigestFormat
import uuid


async def check_and_fix():
    """Check database and fix issues"""
    
    print("=" * 60)
    print("🔍 Checking database for notification issues...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        # Check if tables exist
        try:
            # Test notifications table
            result = await db.execute(text("SELECT COUNT(*) FROM notifications"))
            notif_count = result.scalar()
            print(f"✅ notifications table exists ({notif_count} records)")
        except Exception as e:
            print(f"❌ notifications table missing or error: {e}")
            print("\n⚠️  Run migration: python -m alembic upgrade head")
            return False
        
        try:
            # Test notification_settings table
            result = await db.execute(text("SELECT COUNT(*) FROM notification_settings"))
            settings_count = result.scalar()
            print(f"✅ notification_settings table exists ({settings_count} records)")
        except Exception as e:
            print(f"❌ notification_settings table missing or error: {e}")
            print("\n⚠️  Run migration: python -m alembic upgrade head")
            return False
        
        # Get all users
        result = await db.execute(select(User))
        users = result.scalars().all()
        print(f"\n📊 Found {len(users)} users")
        
        # Check and create preferences
        created_prefs = 0
        created_settings = 0
        
        for user in users:
            # Check UserPreferences
            result = await db.execute(
                select(UserPreferences).where(UserPreferences.user_id == user.id)
            )
            prefs = result.scalar_one_or_none()
            
            if not prefs:
                prefs = UserPreferences(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    subscribed_companies=[],
                    interested_categories=[],
                    keywords=[],
                    notification_frequency=NotificationFrequency.DAILY,
                    digest_enabled=False,
                    digest_frequency=DigestFrequency.DAILY,
                    digest_custom_schedule={},
                    digest_format=DigestFormat.SHORT,
                    digest_include_summaries=True,
                    telegram_chat_id=None,
                    telegram_enabled=False
                )
                db.add(prefs)
                created_prefs += 1
                print(f"  ✅ Created preferences for {user.email}")
            
            # Check NotificationSettings
            result = await db.execute(
                select(NotificationSettings).where(NotificationSettings.user_id == user.id)
            )
            settings = result.scalar_one_or_none()
            
            if not settings:
                settings = NotificationSettings(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    enabled=True,
                    notification_types={},
                    min_priority_score=0.0,
                    company_alerts=True,
                    category_trends=True,
                    keyword_alerts=True
                )
                db.add(settings)
                created_settings += 1
                print(f"  ✅ Created notification settings for {user.email}")
        
        await db.commit()
        
        print("\n" + "=" * 60)
        print("📊 Summary:")
        print(f"  - Created {created_prefs} user preferences")
        print(f"  - Created {created_settings} notification settings")
        print("=" * 60)
        
        if created_prefs > 0 or created_settings > 0:
            print("\n✅ Database fixed! Restart backend and refresh browser.")
        else:
            print("\n✅ All user settings already exist!")
        
        return True


if __name__ == "__main__":
    print("\n🚀 Notification Fix Script\n")
    success = asyncio.run(check_and_fix())
    
    if not success:
        print("\n❌ Fix failed. Check errors above.")
        sys.exit(1)
    else:
        print("\n✅ Done!\n")
        sys.exit(0)



