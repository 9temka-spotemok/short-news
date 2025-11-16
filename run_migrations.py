#!/usr/bin/env python3
"""
Railway Migration Script
Применяет миграции на Railway сервере
"""
import os
import sys
import subprocess
from pathlib import Path

# Получить абсолютный путь к backend
project_root = Path(__file__).parent
backend_dir = project_root / "backend"

# Перейти в директорию backend
os.chdir(backend_dir)

print(f"Working directory: {os.getcwd()}")
print(f"Checking alembic.ini: {Path('alembic.ini').exists()}")

# Проверить DATABASE_URL
db_url = os.environ.get("DATABASE_URL")
db_public_url = os.environ.get("DATABASE_PUBLIC_URL")

if db_url:
    print(f"DATABASE_URL is set: {db_url[:50]}...")
    # Если используется внутренний домен, попробовать использовать публичный URL
    if "railway.internal" in db_url and db_public_url:
        print(f"Using DATABASE_PUBLIC_URL instead of internal URL")
        # Конвертировать в asyncpg формат
        if db_public_url.startswith("postgresql://"):
            db_public_url = db_public_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        os.environ["DATABASE_URL"] = db_public_url
        print(f"Updated DATABASE_URL to use public URL")
else:
    print("WARNING: DATABASE_URL is not set!")

# Выполнить миграции
print("\nRunning migrations...")
result = subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    cwd=backend_dir,
    env=os.environ.copy()
)

if result.returncode == 0:
    print("\n✅ Migrations applied successfully!")
    # Проверить текущую версию
    subprocess.run([sys.executable, "-m", "alembic", "current"], cwd=backend_dir)
else:
    print(f"\n❌ Migration failed with exit code {result.returncode}")

sys.exit(result.returncode)

