# SQL команда для создания таблицы notification_deliveries

## Способ 1: Через Railway CLI

```powershell
railway connect postgres
```

Затем в открывшемся psql выполните:

```sql
-- Создать enum тип
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationdeliverystatus') THEN
        CREATE TYPE notificationdeliverystatus AS ENUM ('pending', 'sent', 'failed', 'cancelled', 'retrying');
    END IF;
END $$;

-- Создать таблицу
CREATE TABLE IF NOT EXISTS notification_deliveries (
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
);

-- Создать индекс
CREATE INDEX IF NOT EXISTS ix_notification_deliveries_status ON notification_deliveries(status);

-- Обновить версию миграции
UPDATE alembic_version SET version_num = '1f2a3b4c5d6e' WHERE version_num IN ('initial_schema', '28c9c8f54d42', 'b5037d3c878c', 'e1f2g3h4i5j6', 'd5e6f7g8h9i0', 'c1d2e3f4g5h6');
```

## Способ 2: Одна команда через psql

```powershell
railway connect postgres -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationdeliverystatus') THEN CREATE TYPE notificationdeliverystatus AS ENUM ('pending', 'sent', 'failed', 'cancelled', 'retrying'); END IF; END \$\$; CREATE TABLE IF NOT EXISTS notification_deliveries (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(), updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(), event_id UUID NOT NULL REFERENCES notification_events(id) ON DELETE CASCADE, channel_id UUID NOT NULL REFERENCES notification_channels(id) ON DELETE CASCADE, status notificationdeliverystatus NOT NULL DEFAULT 'pending', attempt INTEGER NOT NULL DEFAULT 0, last_attempt_at TIMESTAMP WITH TIME ZONE, next_retry_at TIMESTAMP WITH TIME ZONE, response_metadata JSONB NOT NULL DEFAULT '{}', error_message VARCHAR(1000)); CREATE INDEX IF NOT EXISTS ix_notification_deliveries_status ON notification_deliveries(status); UPDATE alembic_version SET version_num = '1f2a3b4c5d6e' WHERE version_num IN ('initial_schema', '28c9c8f54d42', 'b5037d3c878c', 'e1f2g3h4i5j6', 'd5e6f7g8h9i0', 'c1d2e3f4g5h6');"
```

## Способ 3: Через Railway Dashboard

1. Откройте https://railway.app
2. Выберите проект → сервис **web**
3. Перейдите в **Data** → **PostgreSQL** → **Query**
4. Вставьте SQL из файла `create_notification_deliveries_simple.sql`

