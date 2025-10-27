# Railway Database Reset

## Проблема

Миграции Alembic не могут пройти из-за конфликтов с существующими типами и таблицами в базе данных.

## Решение

Используйте скрипт `reset_migrations.py` для полного сброса и пересоздания базы данных.

## Инструкция

### Вариант 1: Railway CLI (рекомендуется)

```bash
# Убедитесь, что вы подключены к правильному проекту Railway
railway login
railway link

# Запустите скрипт сброса
railway run python backend/reset_migrations.py
```

### Вариант 2: Railway Dashboard

1. Откройте проект в Railway Dashboard
2. Перейдите в PostgreSQL сервис
3. Нажмите "Connect" → "Query"
4. Выполните SQL команды из скрипта вручную

### Вариант 3: Локально с подключением к Railway

```bash
# Установите psycopg2-binary локально
pip install psycopg2-binary

# Запустите скрипт локально
railway run python backend/reset_migrations.py
```

## Что делает скрипт

1. ✅ Удаляет таблицу `alembic_version`
2. ✅ Удаляет все существующие таблицы
3. ✅ Удаляет все ENUM типы
4. ✅ Создает PostgreSQL расширения (uuid-ossp, pg_trgm)
5. ✅ Создает все ENUM типы
6. ✅ Создает все таблицы с правильной структурой
7. ✅ Создает все индексы
8. ✅ Помечает миграцию как `initial_schema` в таблице `alembic_version`

## После запуска скрипта

1. Сервисы web, worker, beat автоматически перезапустятся
2. Миграции Alembic не будут запускаться (так как уже помечены как `initial_schema`)
3. Все будущие миграции будут работать корректно

## Проверка

После запуска проверьте логи:

```bash
# Проверьте логи web сервиса
railway logs --service web

# Проверьте логи worker
railway logs --service worker

# Проверьте логи beat
railway logs --service beat
```

Ожидаемый результат:
- ✅ Web: "Creating missing tables if needed..."
- ✅ Web: "Application startup complete!"
- ✅ Worker: "Registered tasks successfully"
- ✅ Beat: "Started periodic tasks"

## Если что-то пошло не так

Если скрипт упал с ошибкой:

```bash
# Удалите все таблицы вручную через Railway Dashboard:
# 1. Откройте PostgreSQL → Connect → Query
# 2. Выполните SQL для удаления всех таблиц
DROP TABLE IF EXISTS alembic_version CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS scraper_state CASCADE;
DROP TABLE IF EXISTS news_keywords CASCADE;
DROP TABLE IF EXISTS user_activity CASCADE;
DROP TABLE IF EXISTS user_preferences CASCADE;
DROP TABLE IF EXISTS news_items CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS companies CASCADE;

# 3. Удалите все типы
DROP TYPE IF EXISTS activitytype CASCADE;
DROP TYPE IF EXISTS notificationfrequency CASCADE;
DROP TYPE IF EXISTS sourcetype CASCADE;
DROP TYPE IF EXISTS news_category CASCADE;
DROP TYPE IF EXISTS telegramdigestmode CASCADE;

# 4. Запустите скрипт снова
railway run python backend/reset_migrations.py
```

