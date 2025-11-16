#!/usr/bin/env python3
"""
Скрипт для отметки проблемной миграции и применения остальных
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

# Использовать публичный URL если доступен
db_url = os.environ.get("DATABASE_URL")
if "railway.internal" in db_url:
    db_public_url = os.environ.get("DATABASE_PUBLIC_URL")
    if db_public_url:
        os.environ["DATABASE_URL"] = db_public_url.replace("postgresql://", "postgresql+asyncpg://")

print("Stamping migration 28c9c8f54d42 as applied...")
result1 = subprocess.run(
    [sys.executable, "-m", "alembic", "stamp", "28c9c8f54d42"],
    cwd=backend_dir,
    env=os.environ.copy()
)

if result1.returncode != 0:
    print(f"❌ Failed to stamp migration: {result1.returncode}")
    sys.exit(1)

print("✅ Migration stamped. Now applying remaining migrations...")
result2 = subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    cwd=backend_dir,
    env=os.environ.copy()
)

if result2.returncode == 0:
    print("\n✅ All migrations applied successfully!")
    subprocess.run([sys.executable, "-m", "alembic", "current"], cwd=backend_dir)
else:
    print(f"\n❌ Migration failed with exit code {result2.returncode}")

sys.exit(result2.returncode)

