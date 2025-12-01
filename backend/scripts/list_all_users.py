"""List all users in the database"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.preferences import UserPreferences

async def list_all_users():
    """List all users with their details"""
    async with AsyncSessionLocal() as db:
        # Get total count
        result = await db.execute(select(func.count(User.id)))
        total = result.scalar()
        print(f"\n{'='*80}")
        print(f"Всего пользователей на платформе: {total}")
        print(f"{'='*80}\n")
        
        if total == 0:
            print("Пользователи не найдены.")
            return
        
        # Get all users
        result = await db.execute(select(User).order_by(User.created_at))
        users = result.scalars().all()
        
        # Get user preferences for subscribed companies count
        for idx, user in enumerate(users, 1):
            # Get user preferences
            prefs_result = await db.execute(
                select(UserPreferences).where(UserPreferences.user_id == user.id)
            )
            user_prefs = prefs_result.scalar_one_or_none()
            
            subscribed_count = 0
            if user_prefs and user_prefs.subscribed_companies:
                subscribed_count = len(user_prefs.subscribed_companies)
            
            print(f"{idx}. Пользователь ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Имя: {user.full_name or 'Не указано'}")
            print(f"   Активен: {'Да' if user.is_active else 'Нет'}")
            print(f"   Верифицирован: {'Да' if user.is_verified else 'Нет'}")
            print(f"   Дата регистрации: {user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else 'Не указано'}")
            print(f"   Последнее обновление: {user.updated_at.strftime('%Y-%m-%d %H:%M:%S') if user.updated_at else 'Не указано'}")
            print(f"   Подписан на компаний: {subscribed_count}")
            print()
        
        print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(list_all_users())






