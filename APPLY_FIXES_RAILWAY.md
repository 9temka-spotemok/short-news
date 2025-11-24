# Инструкция по применению исправлений на Railway

## ⚠️ Важно

**Проблема с event loop** исправляется в коде Python (`backend/app/tasks/digest.py`), а не через SQL. SQL скрипт исправляет только проблемы в базе данных.

## Шаг 1: Применение SQL исправлений

### Вариант A: Python скрипт (РЕКОМЕНДУЕТСЯ) ⭐

Самый простой и безопасный способ - использовать Python скрипт:

```bash
# Вариант 1: Прямой запуск (рекомендуется)
railway run --service web -- python scripts/fix_worker_issues.py

# Вариант 2: Через модульный импорт
railway run --service web -- python -m scripts.fix_worker_issues

# Вариант 3: С явным переходом в директорию
railway run --service web -- sh -c "cd /app && python scripts/fix_worker_issues.py"

# Если вы уже в контейнере (через railway shell):
cd /app
python scripts/fix_worker_issues.py
# или
python -m scripts.fix_worker_issues
```

Скрипт автоматически:
- ✅ Создаст enum типы
- ✅ Добавит колонки в news_items
- ✅ Исправит тип interested_categories
- ✅ Проверит валидность данных
- ✅ Выведет итоговую диагностику

### Вариант B: Через Railway CLI (psql)

```bash
# 1. Подключиться к базе данных
railway connect postgres

# 2. В открывшейся psql консоли выполнить скрипт
# Скопируйте содержимое файла fix_all_worker_issues.sql и вставьте в консоль
```

### Вариант C: Через Railway Dashboard

1. Откройте Railway Dashboard
2. Выберите ваш проект
3. Перейдите в раздел "Postgres"
4. Откройте "Query" или "SQL Console"
5. Скопируйте содержимое `fix_all_worker_issues.sql`
6. Вставьте и выполните

## Шаг 2: Применение исправлений кода (для event loop)

### 1. Закоммитить изменения

```bash
git add backend/app/tasks/digest.py
git commit -m "fix: исправлена проблема с event loop в digest tasks"
git push
```

### 2. Railway автоматически задеплоит изменения

После push в main/master ветку Railway автоматически запустит деплой.

### 3. Перезапустить worker сервис

```bash
# Через Railway CLI
railway restart --service worker

# Или через Dashboard:
# 1. Откройте Railway Dashboard
# 2. Выберите сервис "worker"
# 3. Нажмите "Restart"
```

## Шаг 3: Проверка исправлений

### Проверка SQL исправлений

```bash
railway connect postgres
```

Затем выполните диагностический запрос:

```sql
SELECT 
    '========================================' AS diagnostic
UNION ALL
SELECT 
    '=== ДИАГНОСТИКА WORKER ИСПРАВЛЕНИЙ ==='
UNION ALL
SELECT 
    '========================================'
UNION ALL
SELECT 
    '1. Колонки news_items: ' || 
    CASE 
        WHEN (SELECT COUNT(*) FROM information_schema.columns 
              WHERE table_name = 'news_items' 
              AND column_name IN ('topic', 'sentiment', 'raw_snapshot_url')) = 3
        THEN 'OK (3/3)'
        ELSE 'ERROR'
    END
UNION ALL
SELECT 
    '2. Тип interested_categories: ' || 
    CASE 
        WHEN (SELECT typname FROM pg_type WHERE oid = (
            SELECT typelem FROM pg_type WHERE typname = (
                SELECT udt_name FROM information_schema.columns 
                WHERE table_name = 'user_preferences' AND column_name = 'interested_categories'
            )
        )) = 'newscategory'
        THEN 'OK (newscategory[])'
        ELSE 'ERROR'
    END
UNION ALL
SELECT 
    '3. Enum типы: ' || 
    CASE 
        WHEN (SELECT COUNT(*) FROM pg_type 
              WHERE typname IN ('newscategory', 'newstopic', 'sentimentlabel')) = 3
        THEN 'OK (3/3)'
        ELSE 'ERROR'
    END;
```

### Проверка логов worker

```bash
# Через Railway CLI
railway logs --service worker

# Или через Dashboard:
# 1. Откройте Railway Dashboard
# 2. Выберите сервис "worker"
# 3. Перейдите в раздел "Logs"
# 4. Проверьте, что нет ошибок "Event loop is closed" или "attached to a different loop"
```

## Что исправляет SQL скрипт

1. ✅ Создает enum типы: `newstopic`, `sentimentlabel` (если их нет)
2. ✅ Добавляет колонки в `news_items`: `topic`, `sentiment`, `raw_snapshot_url`
3. ✅ Исправляет тип `interested_categories` с `character varying[]` на `newscategory[]`
4. ✅ Проверяет валидность всех данных
5. ✅ Выводит итоговую диагностику

## Что исправляет код Python

1. ✅ Создает отдельный engine с `NullPool` для задач Celery
2. ✅ Использует `_TaskSessionLocal` вместо общего `AsyncSessionLocal`
3. ✅ Устраняет ошибки "Task got Future attached to a different loop"
4. ✅ Устраняет ошибки "Event loop is closed"

## Порядок применения

**Рекомендуемый порядок:**

1. Сначала применить SQL скрипт (исправляет проблемы в БД)
2. Затем задеплоить изменения кода (исправляет проблему с event loop)
3. Перезапустить worker сервис
4. Проверить логи

## Устранение проблем

### Если SQL скрипт выдает ошибки

- Проверьте, что вы подключены к правильной базе данных
- Убедитесь, что у вас есть права на изменение схемы
- Проверьте логи ошибок в psql консоли

### Если worker все еще выдает ошибки после деплоя

- Убедитесь, что worker сервис перезапущен
- Проверьте, что изменения кода действительно задеплоены
- Проверьте логи worker на наличие других ошибок

### Если ошибки event loop продолжаются

- Убедитесь, что используется последняя версия кода
- Проверьте, что `_TaskSessionLocal` используется во всех async функциях digest
- Проверьте, что engine создан с `NullPool`

