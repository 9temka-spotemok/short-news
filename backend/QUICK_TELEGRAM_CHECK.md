# Быстрая проверка Telegram настроек на Railway

## 1. Проверка через API (самый быстрый способ)

```bash
# Замените YOUR_RAILWAY_URL на URL вашего приложения
# Замените 1018308084 на ваш Chat ID из Telegram

curl https://YOUR_RAILWAY_URL/api/v1/telegram/check-user/1018308084
```

**Что проверить в ответе:**
- `can_use_digest: true` → всё ок, `/digest` должен работать
- `can_use_digest: false` + `exact_match.found: true` + `exact_match.telegram_enabled: false` → нужно включить Telegram уведомления
- `exact_match.found: false` → пользователь не найден, нужно добавить Chat ID

## 2. Проверка через Railway CLI

```bash
# Подключитесь к БД
railway connect postgres

# Выполните SQL запрос
SELECT 
    telegram_chat_id,
    telegram_enabled,
    digest_enabled,
    user_id
FROM user_preferences
WHERE telegram_chat_id = '1018308084';
```

**Если `telegram_enabled = false`, включите:**
```sql
UPDATE user_preferences
SET telegram_enabled = true
WHERE telegram_chat_id = '1018308084';
```

## 3. Проверка через веб-интерфейс

1. Откройте Settings в веб-приложении
2. Убедитесь, что:
   - Chat ID: `1018308084` (точно как в боте, без пробелов)
   - Telegram notifications: **Включено** (toggle активен)
3. Сохраните изменения
4. Попробуйте `/digest` в боте

## 4. Проверка логов после `/digest`

```bash
railway logs
```

Ищите строку:
```
WARNING: User not found for chat_id=1018308084 in handle_digest...
```

Если видите `telegram_enabled=False` → нужно включить в настройках.

## Быстрое исправление через SQL

Если знаете, что пользователь есть, но `telegram_enabled = false`:

```sql
-- Включить Telegram
UPDATE user_preferences
SET telegram_enabled = true
WHERE telegram_chat_id = '1018308084';

-- Проверить
SELECT telegram_chat_id, telegram_enabled FROM user_preferences WHERE telegram_chat_id = '1018308084';
```

После этого `/digest` должен работать!

