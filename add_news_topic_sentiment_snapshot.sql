-- Добавление колонок topic, sentiment и raw_snapshot_url в таблицу news_items
-- Выполните этот скрипт в Railway Dashboard через SQL консоль
-- Этот скрипт соответствует миграции f7a8b9c0d1e2_add_news_topic_sentiment_snapshot

-- Создать enum тип для NewsTopic, если его нет
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'newstopic') THEN
        CREATE TYPE newstopic AS ENUM (
            'product',
            'strategy',
            'finance',
            'technology',
            'security',
            'research',
            'community',
            'talent',
            'regulation',
            'market',
            'other'
        );
    END IF;
END $$;

-- Создать enum тип для SentimentLabel, если его нет
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sentimentlabel') THEN
        CREATE TYPE sentimentlabel AS ENUM (
            'positive',
            'neutral',
            'negative',
            'mixed'
        );
    END IF;
END $$;

-- Добавить колонку topic, если её нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'news_items' 
        AND column_name = 'topic'
    ) THEN
        ALTER TABLE news_items 
        ADD COLUMN topic newstopic;
    END IF;
END $$;

-- Добавить колонку sentiment, если её нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'news_items' 
        AND column_name = 'sentiment'
    ) THEN
        ALTER TABLE news_items 
        ADD COLUMN sentiment sentimentlabel;
    END IF;
END $$;

-- Добавить колонку raw_snapshot_url, если её нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'news_items' 
        AND column_name = 'raw_snapshot_url'
    ) THEN
        ALTER TABLE news_items 
        ADD COLUMN raw_snapshot_url VARCHAR(1000);
    END IF;
END $$;

-- Обновить версию миграции Alembic, если миграция f7a8b9c0d1e2 не была применена
-- Это нужно, чтобы Alembic знал, что миграция уже применена
DO $$
DECLARE
    current_version TEXT;
BEGIN
    -- Получить текущую версию миграции
    SELECT version_num INTO current_version FROM alembic_version LIMIT 1;
    
    -- Если текущая версия b5037d3c88 (предшествующая f7a8b9c0d1e2), обновить до f7a8b9c0d1e2
    IF current_version = 'b5037d3c88' THEN
        UPDATE alembic_version SET version_num = 'f7a8b9c0d1e2';
        RAISE NOTICE 'Updated Alembic version from b5037d3c88 to f7a8b9c0d1e2';
    -- Если версия уже f7a8b9c0d1e2 или более поздняя, не трогать
    ELSIF current_version IS NOT NULL THEN
        RAISE NOTICE 'Current Alembic version is %, no update needed', current_version;
    END IF;
END $$;

