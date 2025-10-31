# Диагностика Telegram бота на Railway

## Проблема
В Telegram боте при выполнении команды `/digest` показывается сообщение "❌ User not found or Telegram not configured", хотя пользователь есть в БД.

## Способы диагностики

### 1. Через API эндпоинт (рекомендуется)

После деплоя на Railway можно проверить пользователя через API:

```bash
# Замените YOUR_RAILWAY_URL на URL вашего приложения на Railway
# Замените 1018308084 на ваш Chat ID

curl https://YOUR_RAILWAY_URL/api/v1/telegram/check-user/1018308084
```

Пример ответа:
```json
{
  "chat_id": "1018308084",
  "exact_match": {
    "found": true,
    "telegram_enabled": false,
    "telegram_chat_id": "1018308084",
    "chat_id_repr": "'1018308084'",
    "user_id": "919e9c66-160d-4578-b6d7-c97f3ff4fd19"
  },
  "trim_match": {
    "found": true,
    "telegram_enabled": false
  },
  "exact_with_enabled": {
    "found": false
  },
  "trim_with_enabled": {
    "found": false
  },
  "user_email": "user@example.com",
  "can_use_digest": false,
  "diagnosis": "⚠️ User found but telegram_enabled == False. Enable Telegram notifications in settings."
}
```

**Интерпретация:**
- Если `exact_match.found = true` и `exact_match.telegram_enabled = false` → проблема в том, что Telegram уведомления не включены
- Если `exact_match.found = false` → пользователь не найден по chat_id
- Если `can_use_digest = true` → `/digest` должен работать

### 2. Через Railway CLI

#### Подключение к базе данных через Railway CLI

```bash
# 1. Установите Railway CLI (если еще не установлен)
npm i -g @railway/cli

# 2. Войдите в Railway
railway login

# 3. Перейдите в проект
railway link

# 4. Подключитесь к PostgreSQL через Railway CLI
railway connect postgres
```

#### Проверка через SQL

После подключения к БД выполните SQL запрос:

```sql
-- Проверка пользователя по chat_id
SELECT 
    up.user_id,
    up.telegram_chat_id,
    up.telegram_enabled,
    up.digest_enabled,
    up.telegram_digest_mode,
    LENGTH(up.telegram_chat_id) as chat_id_length,
    up.telegram_chat_id::text as chat_id_text,
    u.email
FROM user_preferences up
JOIN users u ON u.id = up.user_id
WHERE up.telegram_chat_id = '1018308084';
```

Проверьте:
1. **Есть ли строка?** Если нет → пользователь не добавил Chat ID
2. **`telegram_enabled = true`?** Если `false` → нужно включить Telegram уведомления
3. **`telegram_chat_id` совпадает?** Проверьте, нет ли лишних пробелов
4. **`chat_id_length` правильный?** Должно быть 10 символов (без пробелов)

#### Исправление через SQL (если нужно)

```sql
-- Включить Telegram уведомления для пользователя
UPDATE user_preferences
SET telegram_enabled = true
WHERE telegram_chat_id = '1018308084';

-- Проверить результат
SELECT user_id, telegram_chat_id, telegram_enabled
FROM user_preferences
WHERE telegram_chat_id = '1018308084';
```

### 3. Через Python скрипт (локально, если есть доступ к БД Railway)

```bash
# Установите переменные окружения для подключения к БД Railway
export DATABASE_URL="postgresql://user:password@host:port/dbname"

# Запустите диагностический скрипт
cd backend
poetry run python -m scripts.check_telegram_user 1018308084
```

Скрипт покажет:
- ✅ Найден ли пользователь (exact match)
- ✅ Найден ли пользователь с trim
- ✅ Найден ли пользователь с `telegram_enabled == True`
- ✅ Детальную информацию о настройках

### 4. Проверка через веб-интерфейс

1. Откройте веб-приложение
2. Перейдите в настройки профиля
3. Проверьте:
   - **Chat ID** должен быть точно `1018308084` (без пробелов)
   - **Telegram notifications** должны быть **включены** (toggle должен быть активен)
4. Сохраните настройки
5. Попробуйте `/digest` в боте снова

## Типичные проблемы и решения

### Проблема 1: `telegram_enabled = false`

**Решение:**
- Откройте веб-приложение → Settings → включите "Telegram notifications"
- Или через SQL: `UPDATE user_preferences SET telegram_enabled = true WHERE telegram_chat_id = '1018308084';`

### Проблема 2: Пользователь не найден

**Решение:**
- Убедитесь, что Chat ID добавлен в профиле
- Проверьте, что Chat ID точно совпадает (без пробелов, правильный регистр)
- Попробуйте удалить и добавить Chat ID заново

### Проблема 3: Chat ID с пробелами

**Решение:**
- В веб-интерфейсе удалите и добавьте Chat ID заново
- Или через SQL: `UPDATE user_preferences SET telegram_chat_id = TRIM(telegram_chat_id);`

### Проблема 4: Разные пользователи с одинаковым chat_id

**Решение:**
- Проверьте, нет ли дубликатов: `SELECT user_id, telegram_chat_id FROM user_preferences WHERE telegram_chat_id = '1018308084';`
- Оставьте только один правильный запись, остальные удалите или обновите

## Проверка логов на Railway

После вызова `/digest` в боте проверьте логи на Railway:

```bash
# Через Railway CLI
railway logs

# Или через веб-интерфейс Railway → Logs
```

Ищите строки вида:
```
WARNING: User not found for chat_id=1018308084 in handle_digest. Found user without enabled check: 919e9c66-160d-4578-b6d7-c97f3ff4fd19. telegram_enabled=False
```

Это означает, что пользователь найден, но `telegram_enabled = False`.

## После исправления

1. Проверьте через API: `curl https://YOUR_RAILWAY_URL/api/v1/telegram/check-user/1018308084`
2. Убедитесь, что `can_use_digest = true`
3. Попробуйте `/digest` в боте
4. Проверьте логи на Railway, что нет ошибок

