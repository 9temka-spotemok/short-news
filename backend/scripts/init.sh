#!/bin/bash
set -e

echo "🚀 Starting AI Competitor Insight Hub initialization..."

# Function to wait for database
wait_for_database() {
    echo "⏳ Waiting for database to be ready..."
    python -c "
import asyncio
import asyncpg
import os
import sys

async def wait_for_db():
    max_retries = 30
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            conn = await asyncpg.connect(os.environ['DATABASE_URL'])
            await conn.close()
            print('✅ Database is ready!')
            return
        except Exception as e:
            print(f'⏳ Database not ready (attempt {attempt + 1}/{max_retries}): {e}')
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                print('❌ Database failed to become ready')
                sys.exit(1)

asyncio.run(wait_for_db())
"
}

# Function to apply migrations
apply_migrations() {
    echo "🔄 Applying database migrations..."
    python -m alembic upgrade head
    if [ $? -eq 0 ]; then
        echo "✅ Migrations applied successfully!"
    else
        echo "❌ Failed to apply migrations!"
        exit 1
    fi
}

# Function to check migration status
check_migration_status() {
    echo "📊 Checking migration status..."
    python -m alembic current
}

# Main execution
echo "🔧 Initializing application..."

# Wait for database
wait_for_database

# Apply migrations
apply_migrations

# Check status
check_migration_status

echo "✅ Initialization complete!"
echo "🚀 Starting application..."

# Execute the main command
exec "$@"
