# Руководство по созданию недостающих таблиц вручную

**Дата создания:** 2025-11-17  
**Проблема:** Миграции Alembic не были применены полностью, некоторые таблицы отсутствовали в базе данных  
**Решение:** Создание недостающих таблиц и enum типов напрямую через SQL

---

## 📋 Содержание

1. [Описание проблемы](#описание-проблемы)
2. [Проверка текущего состояния](#проверка-текущего-состояния)
3. [Создание недостающих объектов](#создание-недостающих-объектов)
4. [Проверка результата](#проверка-результата)
5. [Что делать дальше](#что-делать-дальше)

---

## 🔍 Описание проблемы

### Симптомы

- В логах beat сервиса появляется предупреждение:
  ```
  Failed to load dynamic crawl schedule (table/relation not found): ProgrammingError: ...
  ```
- Таблица `crawl_schedules` отсутствует в базе данных
- Некоторые миграции Alembic не были применены полностью

### Причина

Миграции `1b2c3d4e5f67` и части миграции `1f2a3b4c5d6e` не были применены, хотя версия миграций в `alembic_version` указывала на более новую версию (`73b129050e97`).

### Затронутые миграции

1. **Миграция `1b2c3d4e5f67`** (add_competitor_change_events) — не применена полностью
2. **Миграция `1f2a3b4c5d6e`** (add_crawl_and_notification_channels) — применена частично

---

## 🔎 Проверка текущего состояния

### Шаг 1: Подключение к базе данных

```powershell
railway connect postgres
```

### Шаг 2: Проверка текущей версии миграций

```sql
SELECT version_num FROM alembic_version;
```

**Ожидаемый результат:** `73b129050e97` (или другая версия)

### Шаг 3: Проверка наличия таблиц

```sql
-- Проверка таблиц из миграции 1b2c3d4e5f67
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('competitor_pricing_snapshots', 'competitor_change_events')
ORDER BY table_name;

-- Проверка таблиц из миграции 1f2a3b4c5d6e
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'crawl_schedules',
    'source_profiles',
    'crawl_runs',
    'notification_channels',
    'notification_events',
    'notification_subscriptions',
    'notification_deliveries'
)
ORDER BY table_name;
```

### Шаг 4: Проверка enum типов

```sql
-- Проверка enum типов для competitor
SELECT typname 
FROM pg_type 
WHERE typname IN ('competitorprocessingstatus', 'competitornotificationstatus')
ORDER BY typname;

-- Проверка enum типов для crawl
SELECT typname 
FROM pg_type 
WHERE typname IN ('crawlscope', 'crawlmode', 'crawlstatus')
ORDER BY typname;

-- Проверка enum типов для notifications
SELECT typname 
FROM pg_type 
WHERE typname IN ('notification_type', 'notification_priority')
ORDER BY typname;
```

---

## 🛠️ Создание недостающих объектов

### Миграция 1b2c3d4e5f67: Competitor Change Events

#### 1. Создание enum типов

```sql
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'competitorprocessingstatus') THEN
        CREATE TYPE competitorprocessingstatus AS ENUM ('success', 'skipped', 'error');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'competitornotificationstatus') THEN
        CREATE TYPE competitornotificationstatus AS ENUM ('pending', 'sent', 'failed', 'skipped');
    END IF;
END $$;
```

#### 2. Создание таблицы competitor_pricing_snapshots

```sql
CREATE TABLE IF NOT EXISTS competitor_pricing_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    source_url VARCHAR(1000) NOT NULL,
    source_type sourcetype NOT NULL,
    data_hash VARCHAR(64),
    normalized_data JSONB,
    raw_snapshot_url VARCHAR(1000),
    parser_version VARCHAR(32) NOT NULL,
    extracted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    extraction_metadata JSONB NOT NULL DEFAULT '{}',
    warnings JSONB NOT NULL DEFAULT '[]',
    processing_status competitorprocessingstatus NOT NULL DEFAULT 'success',
    processing_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

#### 3. Создание индексов для competitor_pricing_snapshots

```sql
CREATE INDEX IF NOT EXISTS ix_competitor_pricing_snapshot_company_url 
    ON competitor_pricing_snapshots(company_id, source_url);
CREATE INDEX IF NOT EXISTS ix_competitor_pricing_snapshots_data_hash 
    ON competitor_pricing_snapshots(data_hash);
CREATE INDEX IF NOT EXISTS ix_competitor_pricing_snapshots_company_id 
    ON competitor_pricing_snapshots(company_id);
CREATE INDEX IF NOT EXISTS ix_competitor_pricing_snapshots_extracted_at 
    ON competitor_pricing_snapshots(extracted_at);
```

#### 4. Создание таблицы competitor_change_events

```sql
CREATE TABLE IF NOT EXISTS competitor_change_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    source_type sourcetype NOT NULL,
    change_summary TEXT NOT NULL,
    changed_fields JSONB NOT NULL DEFAULT '[]',
    raw_diff JSONB NOT NULL DEFAULT '{}',
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    current_snapshot_id UUID REFERENCES competitor_pricing_snapshots(id) ON DELETE SET NULL,
    previous_snapshot_id UUID REFERENCES competitor_pricing_snapshots(id) ON DELETE SET NULL,
    processing_status competitorprocessingstatus NOT NULL DEFAULT 'success',
    notification_status competitornotificationstatus NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

#### 5. Создание индексов для competitor_change_events

```sql
CREATE INDEX IF NOT EXISTS ix_competitor_change_events_company_detected 
    ON competitor_change_events(company_id, detected_at);
CREATE INDEX IF NOT EXISTS ix_competitor_change_events_company_id 
    ON competitor_change_events(company_id);
CREATE INDEX IF NOT EXISTS ix_competitor_change_events_detected_at 
    ON competitor_change_events(detected_at);
```

---

### Миграция 1f2a3b4c5d6e: Crawl Schedules и Notifications (недостающие части)

#### 1. Создание enum типов для crawl

```sql
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'crawlscope') THEN
        CREATE TYPE crawlscope AS ENUM ('source_type', 'company', 'source');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'crawlmode') THEN
        CREATE TYPE crawlmode AS ENUM ('always_update', 'change_detection');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'crawlstatus') THEN
        CREATE TYPE crawlstatus AS ENUM ('scheduled', 'running', 'success', 'failed', 'skipped');
    END IF;
END $$;
```

#### 2. Создание enum типов для notifications (если отсутствуют)

```sql
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_type') THEN
        CREATE TYPE notification_type AS ENUM (
            'new_news', 
            'company_active', 
            'pricing_change', 
            'funding_announcement',
            'product_launch', 
            'category_trend', 
            'keyword_match', 
            'competitor_milestone'
        );
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_priority') THEN
        CREATE TYPE notification_priority AS ENUM ('low', 'medium', 'high');
    END IF;
END $$;
```

#### 3. Создание таблицы crawl_schedules

```sql
CREATE TABLE IF NOT EXISTS crawl_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    scope crawlscope NOT NULL,
    scope_value VARCHAR(255) NOT NULL,
    mode crawlmode NOT NULL DEFAULT 'always_update',
    frequency_seconds INTEGER NOT NULL DEFAULT 900,
    jitter_seconds INTEGER NOT NULL DEFAULT 300,
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_backoff_seconds INTEGER NOT NULL DEFAULT 60,
    enabled BOOLEAN NOT NULL DEFAULT true,
    priority INTEGER NOT NULL DEFAULT 0,
    run_window_start TIMESTAMP WITH TIME ZONE,
    run_window_end TIMESTAMP WITH TIME ZONE,
    metadata JSONB NOT NULL DEFAULT '{}',
    last_applied_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(scope, scope_value)
);
```

#### 4. Создание индексов для crawl_schedules

```sql
CREATE INDEX IF NOT EXISTS ix_crawl_schedules_scope 
    ON crawl_schedules(scope);
CREATE INDEX IF NOT EXISTS ix_crawl_schedules_scope_value 
    ON crawl_schedules(scope_value);
```

#### 5. Создание таблицы source_profiles

```sql
CREATE TABLE IF NOT EXISTS source_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    source_type sourcetype NOT NULL,
    mode crawlmode NOT NULL DEFAULT 'always_update',
    last_content_hash VARCHAR(255),
    last_run_at TIMESTAMP WITH TIME ZONE,
    last_success_at TIMESTAMP WITH TIME ZONE,
    last_error_at TIMESTAMP WITH TIME ZONE,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    consecutive_no_change INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}',
    schedule_id UUID REFERENCES crawl_schedules(id) ON DELETE SET NULL,
    UNIQUE(company_id, source_type)
);
```

#### 6. Создание индексов для source_profiles

```sql
CREATE INDEX IF NOT EXISTS ix_source_profiles_company_id 
    ON source_profiles(company_id);
CREATE INDEX IF NOT EXISTS ix_source_profiles_source_type 
    ON source_profiles(source_type);
```

#### 7. Создание таблицы crawl_runs

```sql
CREATE TABLE IF NOT EXISTS crawl_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    profile_id UUID NOT NULL REFERENCES source_profiles(id) ON DELETE CASCADE,
    schedule_id UUID REFERENCES crawl_schedules(id) ON DELETE SET NULL,
    status crawlstatus NOT NULL DEFAULT 'scheduled',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    item_count INTEGER NOT NULL DEFAULT 0,
    change_detected BOOLEAN NOT NULL DEFAULT false,
    error_message VARCHAR(1000),
    metadata JSONB NOT NULL DEFAULT '{}'
);
```

#### 8. Создание индексов для crawl_runs

```sql
CREATE INDEX IF NOT EXISTS ix_crawl_runs_profile_id 
    ON crawl_runs(profile_id);
CREATE INDEX IF NOT EXISTS ix_crawl_runs_status 
    ON crawl_runs(status);
```

#### 9. Создание таблицы notification_subscriptions

```sql
CREATE TABLE IF NOT EXISTS notification_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_id UUID NOT NULL REFERENCES notification_channels(id) ON DELETE CASCADE,
    notification_type notification_type NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    frequency VARCHAR(50) NOT NULL DEFAULT 'immediate',
    min_priority notification_priority NOT NULL DEFAULT 'medium',
    filters JSONB NOT NULL DEFAULT '{}',
    UNIQUE(user_id, channel_id, notification_type)
);
```

#### 10. Создание индексов для notification_subscriptions

```sql
CREATE INDEX IF NOT EXISTS ix_notification_subscriptions_user_id 
    ON notification_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS ix_notification_subscriptions_notification_type 
    ON notification_subscriptions(notification_type);
```

---

## ✅ Проверка результата

### Проверка всех таблиц

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'competitor_pricing_snapshots',
    'competitor_change_events',
    'crawl_schedules',
    'source_profiles',
    'crawl_runs',
    'notification_subscriptions'
)
ORDER BY table_name;
```

**Ожидаемый результат:** Все 6 таблиц должны быть в списке

### Проверка всех enum типов

```sql
SELECT typname 
FROM pg_type 
WHERE typname IN (
    'competitorprocessingstatus',
    'competitornotificationstatus',
    'crawlscope',
    'crawlmode',
    'crawlstatus',
    'notification_type',
    'notification_priority'
)
ORDER BY typname;
```

**Ожидаемый результат:** Все 7 enum типов должны быть в списке

### Проверка структуры таблиц

```sql
-- Проверка колонок в crawl_schedules
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'crawl_schedules'
ORDER BY ordinal_position;

-- Проверка индексов
SELECT tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename IN (
    'crawl_schedules',
    'source_profiles',
    'crawl_runs',
    'notification_subscriptions'
)
ORDER BY tablename, indexname;
```

---

## 🚀 Что делать дальше

### 1. Перезапустить сервисы

После создания всех таблиц необходимо перезапустить сервисы в Railway:

1. **Beat сервис** — для применения динамических расписаний
2. **Worker сервис** — для работы с новыми таблицами
3. **Web сервис** — для работы с API

### 2. Проверить логи

После перезапуска проверьте логи beat сервиса:

**До исправления:**
```
WARNING: Failed to load dynamic crawl schedule (table/relation not found): ...
```

**После исправления:**
```
INFO: Loaded X dynamic crawl schedule(s) into beat schedule
```
или
```
DEBUG: No dynamic crawl schedules found, using base schedule only
```

### 3. Проверить работу системы

- Проверьте, что beat сервис запускается без ошибок
- Проверьте, что задачи выполняются корректно
- Проверьте, что динамические расписания загружаются (если они настроены)

---

## 📝 Важные замечания

### О синхронизации с Alembic

Таблицы созданы вручную через SQL, но Alembic может не знать об этом. Это не критично, так как:

1. Все команды используют `CREATE TABLE IF NOT EXISTS` — повторное выполнение безопасно
2. Таблицы уже существуют и система работает
3. При будущих миграциях Alembic может попытаться создать их снова, но это не вызовет ошибок

### Если нужно синхронизировать с Alembic

Если вы хотите, чтобы Alembic знал о примененных миграциях, можно обновить версию вручную:

```sql
-- НЕ РЕКОМЕНДУЕТСЯ без понимания последствий
-- UPDATE alembic_version SET version_num = '1f2a3b4c5d6e' WHERE version_num = '73b129050e97';
```

**Важно:** Это может привести к проблемам, если миграции `2b1c3d4e5f6g` и `73b129050e97` уже применены. Лучше оставить как есть.

### Рекомендации на будущее

1. **Всегда применяйте миграции через Alembic** — это гарантирует правильную последовательность
2. **Проверяйте применение миграций** после деплоя:
   ```bash
   python -m alembic current
   python scripts/check_migrations.py
   ```
3. **Мониторьте логи** сервисов на предмет предупреждений о миграциях
4. **Используйте этот документ** только в экстренных случаях, когда Alembic не работает

---

## 📁 Связанные файлы

- `backend/alembic/versions/1b2c3d4e5f67_add_competitor_change_events.py` — миграция для competitor change events
- `backend/alembic/versions/1f2a3b4c5d6e_add_crawl_and_notification_channels.py` — миграция для crawl schedules и notifications
- `RAILWAY_MIGRATIONS.md` — инструкция по применению миграций на Railway
- `apply_missing_migrations.sql` — полный SQL скрипт для создания всех недостающих объектов

---

## ✅ Чеклист

- [ ] Проверено текущее состояние базы данных
- [ ] Созданы enum типы для competitor processing
- [ ] Создана таблица `competitor_pricing_snapshots`
- [ ] Создана таблица `competitor_change_events`
- [ ] Созданы enum типы для crawl schedules
- [ ] Создана таблица `crawl_schedules`
- [ ] Создана таблица `source_profiles`
- [ ] Создана таблица `crawl_runs`
- [ ] Созданы enum типы для notifications (если отсутствовали)
- [ ] Создана таблица `notification_subscriptions`
- [ ] Проверено наличие всех таблиц
- [ ] Проверено наличие всех enum типов
- [ ] Перезапущены сервисы
- [ ] Проверены логи beat сервиса
- [ ] Система работает корректно

---

**Статус:** ✅ Документ создан  
**Последнее обновление:** 2025-11-17









