#!/usr/bin/env python3
"""
Скрипт для исправления проблем с миграциями на Railway
Исправляет несоответствие версий миграций в базе данных
"""
import os
import sys
import asyncio
from pathlib import Path
import asyncpg

async def fix_migration_version():
    """Исправить версию миграции в базе данных"""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set!")
        return 1
    
    # Конвертировать URL для asyncpg
    # Если используется внутренний домен, попробовать публичный URL
    if "railway.internal" in db_url:
        db_public_url = os.environ.get("DATABASE_PUBLIC_URL")
        if db_public_url:
            print("Using DATABASE_PUBLIC_URL instead of internal URL")
            pg_url = db_public_url
        else:
            pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    else:
        pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        # Подключиться к базе данных
        conn = await asyncpg.connect(pg_url)
        
        # Проверить текущую версию
        version = await conn.fetchval("SELECT version_num FROM alembic_version")
        print(f"Current version in database: {version}")
        
        # Если версия '0001_initial_schema', обновить на 'initial_schema'
        if version == '0001_initial_schema':
            print("Updating version from '0001_initial_schema' to 'initial_schema'...")
            await conn.execute("UPDATE alembic_version SET version_num = 'initial_schema' WHERE version_num = '0001_initial_schema'")
            print("✅ Version updated successfully!")
        elif version:
            print(f"✅ Version is correct: {version}")
        else:
            print("⚠️ No version found in database. You may need to stamp the database.")
        
        await conn.close()
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(fix_migration_version())
    sys.exit(exit_code)

