#!/usr/bin/env python3
"""
Quick table creation script for Railway
"""
import os
import sys
from sqlalchemy import create_engine, text

# Get database URL
db_url = os.environ.get('DATABASE_URL', '')
if not db_url:
    print("❌ DATABASE_URL not found")
    sys.exit(1)

# Convert to sync URL
sync_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')

print("🚀 Creating missing tables...")

try:
    engine = create_engine(sync_url)
    
    with engine.connect() as conn:
        # Read SQL file
        with open('backend/create_missing_tables.sql', 'r') as f:
            sql = f.read()
        
        # Execute SQL
        conn.execute(text(sql))
        conn.commit()
    
    print("✅ Tables created successfully!")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
