"""
Diagnostic script to check Telegram user configuration in database
Usage: python -m scripts.check_telegram_user <chat_id>
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, text
from app.core.database import AsyncSessionLocal
from app.models import UserPreferences, User

async def check_telegram_user(chat_id: str):
    """Check Telegram user configuration for a specific chat_id"""
    chat_id_clean = chat_id.strip()
    
    print(f"\n🔍 Checking Telegram user configuration for chat_id: '{chat_id_clean}'")
    print("=" * 70)
    
    async with AsyncSessionLocal() as db:
        # 1. Check exact match (without trim)
        print("\n1️⃣ Checking EXACT match (without trim):")
        result = await db.execute(
            select(UserPreferences).where(
                UserPreferences.telegram_chat_id == chat_id_clean
            )
        )
        user_prefs_exact = result.scalar_one_or_none()
        
        if user_prefs_exact:
            print(f"   ✅ Found user!")
            print(f"   User ID: {user_prefs_exact.user_id}")
            print(f"   telegram_chat_id: '{user_prefs_exact.telegram_chat_id}'")
            print(f"   telegram_enabled: {user_prefs_exact.telegram_enabled}")
            print(f"   telegram_digest_mode: {user_prefs_exact.telegram_digest_mode}")
            print(f"   digest_enabled: {user_prefs_exact.digest_enabled}")
            print(f"   Chat ID length: {len(user_prefs_exact.telegram_chat_id) if user_prefs_exact.telegram_chat_id else 0}")
            print(f"   Chat ID repr: {repr(user_prefs_exact.telegram_chat_id)}")
            
            # Get user email
            user_result = await db.execute(
                select(User).where(User.id == user_prefs_exact.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                print(f"   User email: {user.email}")
        else:
            print("   ❌ No user found with exact match")
        
        # 2. Check with trim
        print("\n2️⃣ Checking with TRIM (func.trim):")
        result = await db.execute(
            select(UserPreferences).where(
                func.trim(UserPreferences.telegram_chat_id) == chat_id_clean
            )
        )
        user_prefs_trim = result.scalar_one_or_none()
        
        if user_prefs_trim:
            print(f"   ✅ Found user with trim!")
            print(f"   User ID: {user_prefs_trim.user_id}")
            print(f"   telegram_chat_id: '{user_prefs_trim.telegram_chat_id}'")
            print(f"   telegram_enabled: {user_prefs_trim.telegram_enabled}")
            print(f"   Chat ID repr: {repr(user_prefs_trim.telegram_chat_id)}")
        else:
            print("   ❌ No user found with trim")
        
        # 3. Check with telegram_enabled == True (exact)
        print("\n3️⃣ Checking EXACT match WITH telegram_enabled == True:")
        result = await db.execute(
            select(UserPreferences).where(
                UserPreferences.telegram_chat_id == chat_id_clean,
                UserPreferences.telegram_enabled == True
            )
        )
        user_prefs_enabled_exact = result.scalar_one_or_none()
        
        if user_prefs_enabled_exact:
            print(f"   ✅ Found user with telegram_enabled == True!")
        else:
            print("   ❌ No user found with telegram_enabled == True")
            if user_prefs_exact:
                print(f"   ⚠️  User exists but telegram_enabled = {user_prefs_exact.telegram_enabled}")
        
        # 4. Check with trim AND telegram_enabled == True
        print("\n4️⃣ Checking TRIM match WITH telegram_enabled == True:")
        result = await db.execute(
            select(UserPreferences).where(
                func.trim(UserPreferences.telegram_chat_id) == chat_id_clean,
                UserPreferences.telegram_enabled == True
            )
        )
        user_prefs_enabled_trim = result.scalar_one_or_none()
        
        if user_prefs_enabled_trim:
            print(f"   ✅ Found user with trim AND telegram_enabled == True!")
        else:
            print("   ❌ No user found with trim AND telegram_enabled == True")
        
        # 5. Find ALL users with similar chat_id (for debugging)
        print("\n5️⃣ Finding ALL users with similar chat_id (for debugging):")
        result = await db.execute(
            select(UserPreferences).where(
                UserPreferences.telegram_chat_id.like(f"%{chat_id_clean}%")
            )
        )
        all_similar = result.scalars().all()
        
        if all_similar:
            print(f"   Found {len(all_similar)} user(s) with similar chat_id:")
            for pref in all_similar:
                print(f"   - User ID: {pref.user_id}, chat_id: '{pref.telegram_chat_id}', enabled: {pref.telegram_enabled}, repr: {repr(pref.telegram_chat_id)}")
        else:
            print("   No users found with similar chat_id")
        
        # 6. Check raw SQL query
        print("\n6️⃣ Raw SQL check (direct database query):")
        sql_result = await db.execute(
            text(f"""
                SELECT 
                    user_id, 
                    telegram_chat_id, 
                    telegram_enabled,
                    LENGTH(telegram_chat_id) as chat_id_length,
                    telegram_chat_id::text as chat_id_text
                FROM user_preferences 
                WHERE telegram_chat_id = :chat_id
            """),
            {"chat_id": chat_id_clean}
        )
        raw_result = sql_result.fetchone()
        
        if raw_result:
            print(f"   ✅ Found in raw SQL:")
            print(f"   User ID: {raw_result[0]}")
            print(f"   telegram_chat_id: '{raw_result[1]}'")
            print(f"   telegram_enabled: {raw_result[2]}")
            print(f"   chat_id_length: {raw_result[3]}")
            print(f"   chat_id_text: '{raw_result[4]}'")
        else:
            print("   ❌ Not found in raw SQL")
        
        # 7. Summary
        print("\n" + "=" * 70)
        print("📊 SUMMARY:")
        
        if user_prefs_exact:
            if user_prefs_exact.telegram_enabled:
                print("   ✅ User found with telegram_enabled == True")
                print("   ✅ /digest command SHOULD work")
            else:
                print("   ⚠️  User found but telegram_enabled == False")
                print("   ❌ /digest command will NOT work")
                print(f"   💡 Fix: Update telegram_enabled to True for user {user_prefs_exact.user_id}")
        else:
            print("   ❌ User NOT found in database")
            print("   💡 Fix: Add telegram_chat_id to user preferences")
        
        print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.check_telegram_user <chat_id>")
        print("Example: python -m scripts.check_telegram_user 1018308084")
        sys.exit(1)
    
    chat_id = sys.argv[1]
    asyncio.run(check_telegram_user(chat_id))

