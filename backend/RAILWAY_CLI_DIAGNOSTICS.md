# Диагностика Telegram пользователя через Railway CLI

## Быстрая проверка через Railway CLI

### Шаг 1: Подготовка

1. **Установите Railway CLI** (если еще не установлен):
```bash
npm i -g @railway/cli
```

2. **Войдите в Railway**:
```bash
railway login
```

3. **Перейдите в проект**:
```bash
cd backend  # или в корень проекта
railway link
```

### Шаг 2: Подключение к базе данных

```bash
railway connect postgres
```

После выполнения этой команды вы подключитесь к PostgreSQL через psql.

### Шаг 3: Выполнение диагностики

#### Вариант A: Использование SQL скрипта (рекомендуется)

1. **В другой вкладке терминала** скопируйте SQL скрипт:
```bash
# Откройте файл
cat backend/scripts/check_telegram_user_railway.sql
```

2. **В psql сессии** установите переменную с вашим Chat ID и выполните скрипт:

```sql
-- Установите ваш Chat ID (замените на реальный)
\set chat_id '1018308084'

-- Скопируйте и выполните содержимое файла check_telegram_user_railway.sql
-- Или выполните команды по одной (см. Вариант B)
```

#### Вариант B: Выполнение команд по одной

Выполните следующие SQL команды по очереди (замените `1018308084` на ваш Chat ID):

```sql
-- 1. Проверка EXACT MATCH
SELECT 
    up.user_id,
    up.telegram_chat_id,
    up.telegram_enabled,
    up.digest_enabled,
    LENGTH(up.telegram_chat_id) as chat_id_length,
    u.email as user_email,
    CASE 
        WHEN up.telegram_enabled = true THEN '✅ Telegram enabled'
        WHEN up.telegram_enabled = false THEN '❌ Telegram DISABLED'
        ELSE '⚠️ NULL'
    END as status
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE up.telegram_chat_id = '1018308084';
```

```sql
-- 2. Проверка с TRIM
SELECT 
    up.user_id,
    up.telegram_chat_id,
    up.telegram_enabled,
    TRIM(up.telegram_chat_id) as trimmed_chat_id,
    u.email as user_email
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE TRIM(up.telegram_chat_id) = '1018308084';
```

```sql
-- 3. Проверка с telegram_enabled = TRUE
SELECT 
    up.user_id,
    up.telegram_chat_id,
    up.telegram_enabled,
    u.email as user_email,
    '✅ /digest должен работать' as status
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE up.telegram_chat_id = '1018308084'
  AND up.telegram_enabled = true;
```

```sql
-- 4. ИТОГОВАЯ ДИАГНОСТИКА
SELECT 
    COUNT(*) FILTER (WHERE up.telegram_chat_id = '1018308084') as exact_match_count,
    COUNT(*) FILTER (WHERE up.telegram_chat_id = '1018308084' AND up.telegram_enabled = true) as enabled_count,
    CASE 
        WHEN COUNT(*) FILTER (WHERE up.telegram_chat_id = '1018308084' AND up.telegram_enabled = true) > 0
        THEN '✅ /digest ДОЛЖЕН РАБОТАТЬ'
        WHEN COUNT(*) FILTER (WHERE up.telegram_chat_id = '1018308084') > 0
        THEN '⚠️ Пользователь найден, но telegram_enabled = false'
        ELSE '❌ Пользователь НЕ НАЙДЕН'
    END as diagnosis
FROM user_preferences up
WHERE up.telegram_chat_id = '1018308084';
```

## Интерпретация результатов

### ✅ Пользователь найден и telegram_enabled = true
```
exact_match_count: 1
enabled_count: 1
diagnosis: ✅ /digest ДОЛЖЕН РАБОТАТЬ
```
→ **Всё должно работать!** Если `/digest` не работает, проверьте логи на Railway.

### ⚠️ Пользователь найден, но telegram_enabled = false
```
exact_match_count: 1
enabled_count: 0
diagnosis: ⚠️ Пользователь найден, но telegram_enabled = false
```
→ **Нужно включить Telegram уведомления!**

### ❌ Пользователь не найден
```
exact_match_count: 0
enabled_count: 0
diagnosis: ❌ Пользователь НЕ НАЙДЕН
```
→ **Нужно добавить Chat ID в профиль.**

## Быстрое исправление через SQL

Если пользователь найден, но `telegram_enabled = false`:

```sql
-- Включить Telegram уведомления
UPDATE user_preferences
SET telegram_enabled = true
WHERE telegram_chat_id = '1018308084';

-- Проверить результат
SELECT 
    telegram_chat_id,
    telegram_enabled,
    digest_enabled
FROM user_preferences
WHERE telegram_chat_id = '1018308084';
```

Если нужно также обновить Chat ID (на случай пробелов):

```sql
-- Убрать пробелы из chat_id
UPDATE user_preferences
SET telegram_chat_id = TRIM(telegram_chat_id)
WHERE telegram_chat_id LIKE '%1018308084%';

-- Проверить
SELECT telegram_chat_id, LENGTH(telegram_chat_id) as length
FROM user_preferences
WHERE telegram_chat_id LIKE '%1018308084%';
```

## Полная проверка всех настроек пользователя

```sql
-- Полная информация о пользователе
SELECT 
    u.email,
    up.telegram_chat_id,
    up.telegram_enabled,
    up.digest_enabled,
    up.digest_frequency,
    up.telegram_digest_mode,
    up.interested_categories,
    array_length(up.subscribed_companies, 1) as companies_count
FROM user_preferences up
JOIN users u ON u.id = up.user_id
WHERE up.telegram_chat_id = '1018308084'
   OR TRIM(up.telegram_chat_id) = '1018308084';
```

## Проверка логов после исправления

После исправления настроек проверьте логи:

```bash
# В отдельной вкладке терминала
railway logs

# Или в веб-интерфейсе Railway → Logs
```

Попробуйте `/digest` в боте и посмотрите логи. Не должно быть:
```
WARNING: User not found for chat_id=1018308084... telegram_enabled=False
```

## Альтернативный способ: через Railway переменные

Если нужно подключиться к БД с другой машины:

```bash
# Получить DATABASE_URL из Railway
railway variables

# Подключиться через psql
psql $DATABASE_URL
```

Затем выполните SQL команды из раздела выше.

