# Проверка enum типов в Railway базе данных

## Проблема

В локальной базе данных enum типы могут быть названы без подчеркивания:
- `digestfrequency` вместо `digest_frequency`
- `digestformat` вместо `digest_format`
- `telegramdigestmode` вместо `telegram_digest_mode`

Это вызывает ошибки при обновлении через ORM SQLAlchemy, так как он пытается использовать имена с подчеркиванием.

## Решение в коде

Код был исправлен для использования прямых SQL UPDATE запросов с явным CAST:
```sql
CAST(:value AS text)::digestfrequency
```

Это работает для обеих версий имен (старых и новых).

## Проверка через Railway CLI

### Вариант 1: Через Railway CLI run команду

```bash
# Запустить скрипт проверки в Railway
railway run --service web -- python backend/scripts/check_railway_enum_types.py
```

### Вариант 2: Прямой SQL запрос через Railway CLI

```bash
# Подключиться к базе данных Railway через CLI
railway connect postgres

# Затем выполнить SQL запрос:
```

```sql
-- Проверить все enum типы
SELECT 
    t.typname as enum_name,
    string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) as enum_values
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname IN (
    'digestfrequency', 'digest_frequency',
    'digestformat', 'digest_format',
    'telegramdigestmode', 'telegram_digest_mode',
    'notificationfrequency', 'notification_frequency'
)
GROUP BY t.typname
ORDER BY t.typname;
```

```sql
-- Проверить конкретные enum типы
SELECT EXISTS (
    SELECT 1 FROM pg_type WHERE typname = 'digestfrequency'
) as has_old_digest_frequency,
EXISTS (
    SELECT 1 FROM pg_type WHERE typname = 'digest_frequency'
) as has_new_digest_frequency;

SELECT EXISTS (
    SELECT 1 FROM pg_type WHERE typname = 'digestformat'
) as has_old_digest_format,
EXISTS (
    SELECT 1 FROM pg_type WHERE typname = 'digest_format'
) as has_new_digest_format;

SELECT EXISTS (
    SELECT 1 FROM pg_type WHERE typname = 'telegramdigestmode'
) as has_old_telegram_digest_mode,
EXISTS (
    SELECT 1 FROM pg_type WHERE typname = 'telegram_digest_mode'
) as has_new_telegram_digest_mode;
```

```sql
-- Проверить определения колонок
SELECT 
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_name = 'user_preferences'
  AND column_name IN ('digest_frequency', 'digest_format', 'telegram_digest_mode')
ORDER BY column_name;
```

### Вариант 3: Через Railway Dashboard

1. Откройте Railway Dashboard
2. Выберите проект → PostgreSQL сервис
3. Перейдите во вкладку "Data" или "Query"
4. Выполните SQL запросы из варианта 2

## Интерпретация результатов

### Если найден старый формат (без подчеркивания):
```
has_old_digest_frequency: true
has_new_digest_frequency: false
```
⚠️ **База использует старые имена enum типов**
- ✅ Текущий код уже исправлен для работы с этим
- ✅ Используются прямые SQL UPDATE с CAST
- ✅ Дополнительных действий не требуется

### Если найден новый формат (с подчеркиванием):
```
has_old_digest_frequency: false
has_new_digest_frequency: true
```
✅ **База использует новые имена enum типов**
- ✅ ORM обновления должны работать
- ✅ Прямой SQL также будет работать

### Если найдены оба:
```
has_old_digest_frequency: true
has_new_digest_frequency: true
```
⚠️ **Оба имени существуют**
- ⚠️ Нужно проверить, какой используется в колонках
- ⚠️ Возможно, нужна миграция для удаления старых типов

## Проверка через Python скрипт

Если переменные окружения Railway настроены локально:

```bash
# Установить переменные окружения Railway
railway variables --service web --json > .env.railway

# Загрузить и запустить
source .env.railway  # Linux/Mac
# или
# В PowerShell: Get-Content .env.railway | ForEach-Object { ... }

python backend/scripts/check_railway_enum_types.py
```

## Рекомендации

1. **Текущее решение работает для обеих версий** - код использует CAST, который обрабатывает оба формата
2. **Для будущего** - желательно привести к единому формату (с подчеркиванием) через миграцию
3. **Мониторинг** - периодически проверять логи на ошибки enum типов



















