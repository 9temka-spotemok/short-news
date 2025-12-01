# SQL команды для диагностики Railway системы

## Подключение к базе данных через Railway CLI

### Шаг 1: Подготовка

```bash
# Установка Railway CLI (если еще не установлен)
npm i -g @railway/cli

# Вход в Railway
railway login

# Переход в проект
cd backend  # или в корень проекта
railway link
```

### Шаг 2: Подключение к PostgreSQL

```bash
railway connect postgres
```

После выполнения этой команды вы подключитесь к PostgreSQL через `psql`.

---

## 🔍 Базовые диагностические команды

### 1. Проверка версии PostgreSQL и подключения

```sql
-- Версия PostgreSQL
SELECT version();

-- Текущая база данных
SELECT current_database();

-- Текущий пользователь
SELECT current_user;

-- Время сервера
SELECT NOW();

-- Проверка подключения
SELECT 1 as connection_test;
```

### 2. Проверка расширений PostgreSQL

```sql
-- Список установленных расширений
SELECT 
    extname as extension_name,
    extversion as version
FROM pg_extension
ORDER BY extname;

-- Проверка необходимых расширений
SELECT 
    CASE WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp') 
         THEN '✅ uuid-ossp установлен' 
         ELSE '❌ uuid-ossp НЕ установлен' 
    END as uuid_extension,
    CASE WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') 
         THEN '✅ pg_trgm установлен' 
         ELSE '❌ pg_trgm НЕ установлен' 
    END as trigram_extension;
```

### 3. Проверка состояния миграций Alembic

```sql
-- Текущая версия миграции
SELECT version_num, version_num as current_migration
FROM alembic_version;

-- Проверка существования таблицы миграций
SELECT 
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version')
         THEN '✅ Таблица alembic_version существует'
         ELSE '❌ Таблица alembic_version НЕ существует'
    END as alembic_status;
```

---

## 📊 Диагностика структуры базы данных

### 4. Список всех таблиц

```sql
-- Все таблицы в базе данных
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY tablename;

-- Количество таблиц
SELECT COUNT(*) as total_tables
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
```

### 5. Проверка основных таблиц приложения

```sql
-- Проверка существования основных таблиц
SELECT 
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') 
         THEN '✅ users' 
         ELSE '❌ users НЕ существует' 
    END as users_table,
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_preferences') 
         THEN '✅ user_preferences' 
         ELSE '❌ user_preferences НЕ существует' 
    END as user_preferences_table,
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'news_items') 
         THEN '✅ news_items' 
         ELSE '❌ news_items НЕ существует' 
    END as news_items_table,
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'companies') 
         THEN '✅ companies' 
         ELSE '❌ companies НЕ существует' 
    END as companies_table,
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notification_events') 
         THEN '✅ notification_events' 
         ELSE '❌ notification_events НЕ существует' 
    END as notification_events_table,
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notification_channels') 
         THEN '✅ notification_channels' 
         ELSE '❌ notification_channels НЕ существует' 
    END as notification_channels_table,
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notification_deliveries') 
         THEN '✅ notification_deliveries' 
         ELSE '❌ notification_deliveries НЕ существует' 
    END as notification_deliveries_table;
```

### 6. Структура конкретной таблицы

```sql
-- Замените 'users' на нужную таблицу
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;
```

### 7. Проверка индексов

```sql
-- Все индексы в базе данных
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY tablename, indexname;

-- Индексы для конкретной таблицы
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'users'
ORDER BY indexname;
```

### 8. Проверка внешних ключей (Foreign Keys)

```sql
-- Все внешние ключи
SELECT
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    tc.constraint_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name;
```

---

## 📈 Статистика и размеры

### 9. Размер базы данных и таблиц

```sql
-- Размер всей базы данных
SELECT 
    pg_size_pretty(pg_database_size(current_database())) as database_size;

-- Размер всех таблиц
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 10. Количество записей в таблицах

```sql
-- Количество записей в основных таблицах
SELECT 
    'users' as table_name, 
    COUNT(*) as row_count 
FROM users
UNION ALL
SELECT 
    'user_preferences', 
    COUNT(*) 
FROM user_preferences
UNION ALL
SELECT 
    'news_items', 
    COUNT(*) 
FROM news_items
UNION ALL
SELECT 
    'companies', 
    COUNT(*) 
FROM companies
UNION ALL
SELECT 
    'notification_events', 
    COUNT(*) 
FROM notification_events
UNION ALL
SELECT 
    'notification_channels', 
    COUNT(*) 
FROM notification_channels
UNION ALL
SELECT 
    'notification_deliveries', 
    COUNT(*) 
FROM notification_deliveries
ORDER BY row_count DESC;
```

---

## 👥 Диагностика пользователей

### 11. Статистика пользователей

```sql
-- Общая статистика пользователей
SELECT 
    COUNT(*) as total_users,
    COUNT(*) FILTER (WHERE is_active = true) as active_users,
    COUNT(*) FILTER (WHERE is_verified = true) as verified_users,
    COUNT(*) FILTER (WHERE is_active = false) as inactive_users
FROM users;

-- Пользователи с настройками Telegram
SELECT 
    COUNT(*) as users_with_telegram,
    COUNT(*) FILTER (WHERE telegram_enabled = true) as telegram_enabled,
    COUNT(*) FILTER (WHERE digest_enabled = true) as digest_enabled
FROM user_preferences
WHERE telegram_chat_id IS NOT NULL;
```

### 12. Последние зарегистрированные пользователи

```sql
-- Последние 10 пользователей
SELECT 
    id,
    email,
    full_name,
    is_active,
    is_verified,
    created_at
FROM users
ORDER BY created_at DESC
LIMIT 10;
```

---

## 📰 Диагностика новостей

### 13. Статистика новостей

```sql
-- Статистика новостей по категориям
SELECT 
    category,
    COUNT(*) as count,
    MAX(created_at) as latest_news
FROM news_items
GROUP BY category
ORDER BY count DESC;

-- Последние новости
SELECT 
    id,
    title,
    category,
    source_type,
    created_at
FROM news_items
ORDER BY created_at DESC
LIMIT 10;
```

### 14. Новости по источникам

```sql
-- Статистика по источникам
SELECT 
    source_type,
    COUNT(*) as count,
    COUNT(DISTINCT company_id) as unique_companies
FROM news_items
GROUP BY source_type
ORDER BY count DESC;
```

---

## 🔔 Диагностика уведомлений

### 15. Статистика уведомлений

```sql
-- Статистика событий уведомлений
SELECT 
    status,
    COUNT(*) as count
FROM notification_events
GROUP BY status
ORDER BY count DESC;

-- Статистика доставок уведомлений
SELECT 
    status,
    COUNT(*) as count,
    AVG(attempt) as avg_attempts
FROM notification_deliveries
GROUP BY status
ORDER BY count DESC;
```

### 16. Проблемные доставки

```sql
-- Неудачные доставки
SELECT 
    id,
    event_id,
    channel_id,
    status,
    attempt,
    error_message,
    last_attempt_at
FROM notification_deliveries
WHERE status IN ('failed', 'retrying')
ORDER BY last_attempt_at DESC
LIMIT 20;
```

---

## 🔌 Диагностика подключений

### 17. Активные подключения к базе данных

```sql
-- Текущие подключения
SELECT 
    pid,
    usename as username,
    application_name,
    client_addr,
    state,
    query_start,
    state_change,
    wait_event_type,
    wait_event,
    query
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid != pg_backend_pid()
ORDER BY query_start;
```

### 18. Статистика подключений

```sql
-- Общая статистика подключений
SELECT 
    COUNT(*) as total_connections,
    COUNT(*) FILTER (WHERE state = 'active') as active_connections,
    COUNT(*) FILTER (WHERE state = 'idle') as idle_connections,
    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
FROM pg_stat_activity
WHERE datname = current_database();
```

---

## 🔍 Проверка целостности данных

### 19. Проверка orphaned записей

```sql
-- User preferences без пользователя
SELECT 
    up.id,
    up.user_id,
    up.telegram_chat_id
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE u.id IS NULL;

-- News items без компании
SELECT 
    ni.id,
    ni.title,
    ni.company_id
FROM news_items ni
LEFT JOIN companies c ON c.id = ni.company_id
WHERE ni.company_id IS NOT NULL AND c.id IS NULL;
```

### 20. Проверка NULL значений в критических полях

```sql
-- Пользователи без email
SELECT COUNT(*) as users_without_email
FROM users
WHERE email IS NULL OR email = '';

-- User preferences без user_id
SELECT COUNT(*) as preferences_without_user
FROM user_preferences
WHERE user_id IS NULL;
```

---

## ⚡ Производительность

### 21. Медленные запросы (требует pg_stat_statements)

```sql
-- Проверка наличия расширения
SELECT 
    CASE WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')
         THEN '✅ pg_stat_statements доступен'
         ELSE '❌ pg_stat_statements НЕ установлен'
    END as extension_status;

-- Если установлен, можно посмотреть статистику запросов
-- SELECT * FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;
```

### 22. Статистика использования таблиц

```sql
-- Статистика по таблицам
SELECT 
    schemaname,
    relname as table_name,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

---

## 🛠️ Быстрая диагностика (все в одном)

### 23. Комплексная диагностика системы

```sql
-- Полная диагностика системы
SELECT 
    'PostgreSQL Version' as check_type,
    version() as result
UNION ALL
SELECT 
    'Database Size',
    pg_size_pretty(pg_database_size(current_database()))
UNION ALL
SELECT 
    'Total Tables',
    COUNT(*)::text
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
UNION ALL
SELECT 
    'Total Users',
    COUNT(*)::text
FROM users
UNION ALL
SELECT 
    'Active Users',
    COUNT(*)::text
FROM users
WHERE is_active = true
UNION ALL
SELECT 
    'Total News Items',
    COUNT(*)::text
FROM news_items
UNION ALL
SELECT 
    'Active Connections',
    COUNT(*)::text
FROM pg_stat_activity
WHERE datname = current_database()
UNION ALL
SELECT 
    'Alembic Version',
    COALESCE(version_num, 'NOT FOUND')
FROM alembic_version;
```

---

## 📝 Полезные команды psql

После подключения через `railway connect postgres` вы можете использовать:

```sql
-- Список всех команд psql
\?

-- Список всех таблиц
\dt

-- Структура таблицы
\d table_name

-- Список всех баз данных
\l

-- Выход из psql
\q

-- Показать все переменные
\set

-- Включить тайминг запросов
\timing

-- Расширенный вывод
\x
```

---

## 🚨 Частые проблемы и их диагностика

### Проблема: Миграции не применяются

```sql
-- Проверка версии миграции
SELECT version_num FROM alembic_version;

-- Проверка существования всех таблиц из миграций
SELECT 
    table_name,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = t.table_name
    ) THEN '✅' ELSE '❌' END as exists
FROM (
    VALUES 
        ('users'),
        ('user_preferences'),
        ('news_items'),
        ('companies'),
        ('notification_events'),
        ('notification_channels'),
        ('notification_deliveries')
) AS t(table_name);
```

### Проблема: Медленная работа базы данных

```sql
-- Проверка размера таблиц (большие таблицы могут быть медленными)
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;

-- Проверка необходимости VACUUM
SELECT 
    schemaname,
    relname,
    n_dead_tup,
    n_live_tup,
    CASE 
        WHEN n_live_tup > 0 
        THEN ROUND(100.0 * n_dead_tup / n_live_tup, 2)
        ELSE 0
    END as dead_tuple_percent
FROM pg_stat_user_tables
WHERE n_dead_tup > 0
ORDER BY dead_tuple_percent DESC;
```

### Проблема: Проблемы с подключениями

```sql
-- Проверка лимита подключений
SHOW max_connections;

-- Текущие подключения
SELECT COUNT(*) as current_connections
FROM pg_stat_activity
WHERE datname = current_database();
```

---

## 💡 Советы по использованию

1. **Сохраняйте результаты**: Используйте `\o filename.txt` для сохранения вывода в файл
2. **Форматирование**: Используйте `\x` для расширенного формата вывода
3. **Тайминг**: Используйте `\timing` для измерения времени выполнения запросов
4. **Экспорт**: Используйте `\copy` для экспорта данных в CSV

---

## 📚 Дополнительные ресурсы

- [Railway CLI Documentation](https://docs.railway.app/develop/cli)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)














