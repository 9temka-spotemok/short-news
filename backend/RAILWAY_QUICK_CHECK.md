# Быстрая диагностика через Railway CLI

## Пошаговая инструкция

### 1. Подключение к Railway

```bash
# Установите Railway CLI (если нужно)
npm i -g @railway/cli

# Войдите в Railway
railway login

# Перейдите в проект
cd backend  # или корень проекта
railway link
```

### 2. Подключение к базе данных

```bash
railway connect postgres
```

После выполнения вы окажетесь в psql сессии.

### 3. Выполнение диагностики

**Скопируйте и выполните эту команду** (замените `1018308084` на ваш Chat ID):

```sql
-- Основная проверка
SELECT 
    up.user_id,
    up.telegram_chat_id,
    up.telegram_enabled,
    up.digest_enabled,
    u.email as user_email,
    CASE 
        WHEN up.telegram_enabled = true THEN '✅ Telegram enabled - /digest ДОЛЖЕН работать'
        WHEN up.telegram_enabled = false THEN '❌ Telegram DISABLED - нужно включить!'
        ELSE '⚠️ telegram_enabled is NULL'
    END as status
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE up.telegram_chat_id = '1018308084';
```

### 4. Интерпретация результата

**Если видите:**
- `telegram_enabled: true` → ✅ Всё ок, `/digest` должен работать!
- `telegram_enabled: false` → ⚠️ Нужно включить Telegram уведомления
- Пустой результат → ❌ Пользователь не найден, нужно добавить Chat ID

### 5. Быстрое исправление (если telegram_enabled = false)

```sql
-- Включить Telegram уведомления
UPDATE user_preferences
SET telegram_enabled = true
WHERE telegram_chat_id = '1018308084';

-- Проверить результат
SELECT telegram_chat_id, telegram_enabled 
FROM user_preferences 
WHERE telegram_chat_id = '1018308084';
```

### 6. Полная диагностика (если нужно больше информации)

Используйте файл `backend/scripts/check_telegram_user_simple.sql`:

1. Откройте файл в редакторе
2. Замените `1018308084` на ваш Chat ID во всех местах
3. Скопируйте и выполните SQL команды в psql

Или выполните готовый скрипт:

```sql
-- В psql выполните:
\i backend/scripts/check_telegram_user_simple.sql
```

(Но сначала замените `1018308084` на ваш Chat ID в файле)

## Альтернатива: через готовый скрипт

```bash
# 1. Отредактируйте файл, заменив Chat ID
nano backend/scripts/check_telegram_user_simple.sql
# или
code backend/scripts/check_telegram_user_simple.sql

# 2. Подключитесь к Railway
railway connect postgres

# 3. Выполните скрипт
\i /full/path/to/check_telegram_user_simple.sql
```

## Выход из psql

```sql
\q
```

## Проверка после исправления

После того как включите `telegram_enabled = true`, попробуйте:

1. Отправить `/digest` в Telegram боте
2. Проверить логи: `railway logs` (в другой вкладке)
3. Убедиться, что нет ошибок в логах

## Если пользователь не найден

Если результат пустой, значит Chat ID не добавлен в профиль:

1. Откройте веб-приложение
2. Перейдите в Settings
3. Добавьте Chat ID: `1018308084`
4. Включите "Telegram notifications"
5. Сохраните изменения

Затем проверьте снова через SQL.

