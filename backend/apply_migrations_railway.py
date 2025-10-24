#!/usr/bin/env python3
"""
Railway Migration Helper
Применяет миграции с нуля для новой базы данных на Railway
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    print("🚀 Railway Migration Helper")
    print("=" * 50)
    
    # Check if DATABASE_URL is set
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set!")
        print("Please set DATABASE_URL environment variable")
        return 1
    
    print(f"✅ DATABASE_URL configured")
    
    # Convert to asyncpg URL if needed
    if db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        print(f"✅ Converted to asyncpg URL")
    
    # Run migrations
    print("\n📦 Running migrations...")
    try:
        result = subprocess.run(
            ["python", "-m", "alembic", "upgrade", "head"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Migrations applied successfully!")
            if result.stdout:
                print(result.stdout)
            return 0
        else:
            print("❌ Migration failed!")
            print(result.stderr)
            return 1
            
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
