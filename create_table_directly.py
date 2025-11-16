#!/usr/bin/env python3
"""
Создание таблицы notification_deliveries напрямую через SQL
Обходит проблемы с миграциями
"""
import os
import sys
import asyncio
import asyncpg

async def create_table():
    """Создать таблицу notification_deliveries напрямую"""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set!")
        return 1
    
    # Конвертировать URL для asyncpg
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
        
        print("✅ Connected to database")
        
        # Создать enum тип, если его нет
        print("Creating enum type notificationdeliverystatus...")
        await conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationdeliverystatus') THEN
                    CREATE TYPE notificationdeliverystatus AS ENUM ('pending', 'sent', 'failed', 'cancelled', 'retrying');
                END IF;
            END $$;
        """)
        print("✅ Enum type created or already exists")
        
        # Проверить, существует ли таблица notification_channels (зависимость)
        channels_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'notification_channels'
            )
        """)
        
        if not channels_exists:
            print("⚠️ WARNING: notification_channels table does not exist!")
            print("   You need to create notification_channels first.")
            await conn.close()
            return 1
        
        # Проверить, существует ли таблица notification_events (зависимость)
        events_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'notification_events'
            )
        """)
        
        if not events_exists:
            print("⚠️ WARNING: notification_events table does not exist!")
            print("   You need to create notification_events first.")
            await conn.close()
            return 1
        
        # Проверить, существует ли уже таблица
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'notification_deliveries'
            )
        """)
        
        if table_exists:
            print("✅ Table notification_deliveries already exists!")
        else:
            # Создать таблицу
            print("Creating table notification_deliveries...")
            await conn.execute("""
                CREATE TABLE notification_deliveries (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    event_id UUID NOT NULL REFERENCES notification_events(id) ON DELETE CASCADE,
                    channel_id UUID NOT NULL REFERENCES notification_channels(id) ON DELETE CASCADE,
                    status notificationdeliverystatus NOT NULL DEFAULT 'pending',
                    attempt INTEGER NOT NULL DEFAULT 0,
                    last_attempt_at TIMESTAMP WITH TIME ZONE,
                    next_retry_at TIMESTAMP WITH TIME ZONE,
                    response_metadata JSONB NOT NULL DEFAULT '{}',
                    error_message VARCHAR(1000)
                )
            """)
            print("✅ Table notification_deliveries created!")
        
        # Создать индекс, если его нет
        print("Creating index on status...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_notification_deliveries_status 
            ON notification_deliveries(status)
        """)
        print("✅ Index created or already exists")
        
        # Обновить версию миграции
        print("Updating alembic version to 1f2a3b4c5d6e...")
        current_version = await conn.fetchval("SELECT version_num FROM alembic_version")
        print(f"Current version: {current_version}")
        
        await conn.execute("""
            UPDATE alembic_version 
            SET version_num = '1f2a3b4c5d6e' 
            WHERE version_num IN ('initial_schema', '28c9c8f54d42', 'b5037d3c878c', 'e1f2g3h4i5j6', 'd5e6f7g8h9i0', 'c1d2e3f4g5h6')
        """)
        
        new_version = await conn.fetchval("SELECT version_num FROM alembic_version")
        print(f"✅ Version updated to: {new_version}")
        
        await conn.close()
        print("\n🎉 Success! Table notification_deliveries is ready!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(create_table())
    sys.exit(exit_code)

