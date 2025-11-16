# Тестирование кнопок Telegram бота через Railway CLI

## Описание

Этот скрипт позволяет протестировать работу кнопок `digest_settings_all` и `digest_settings_tracked` на проде через Railway webhook без необходимости взаимодействовать с Telegram ботом вручную.

## Предварительные требования

1. **Railway CLI установлен:**
   ```bash
   npm i -g @railway/cli
   railway login
   ```

2. **Python зависимости:**
   ```bash
   cd backend
   poetry install  # или pip install -r requirements.txt
   ```

3. **Доступ к Railway проекту:**
   ```bash
   cd backend
   railway link
   ```

## Использование

### Тестирование одной кнопки

#### Тестирование кнопки "All News"
```bash
python -m scripts.test_telegram_buttons_railway \
  --chat-id 1018308084 \
  --button digest_settings_all \
  --webhook-url https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook
```

#### Тестирование кнопки "Tracked Only"
```bash
python -m scripts.test_telegram_buttons_railway \
  --chat-id 1018308084 \
  --button digest_settings_tracked \
  --webhook-url https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook
```

### Тестирование обеих кнопок подряд

```bash
python -m scripts.test_telegram_buttons_railway \
  --chat-id 1018308084 \
  --button all \
  --webhook-url https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook
```

### Использование webhook URL по умолчанию

Если не указывать `--webhook-url`, будет использован Railway production URL по умолчанию:

```bash
python -m scripts.test_telegram_buttons_railway \
  --chat-id 1018308084 \
  --button digest_settings_all
```

## Проверка результатов

### Шаг 1: Проверка логов Railway

После выполнения скрипта проверьте логи:

```bash
# Проверка логов за последние 2 минуты
railway logs --service "web" --since 2m | grep -i "callback\|digest_settings"

# Или все логи за последнюю минуту
railway logs --service "web" --since 1m
```

### Шаг 2: Что искать в логах

Успешная обработка callback должна содержать:

```
INFO: Received Telegram webhook: {...}
INFO: Processing callback from <chat_id>: digest_settings_all
INFO: Digest mode changed to all for user <user_id> (chat_id: <chat_id>)
```

Или для `digest_settings_tracked`:

```
INFO: Received Telegram webhook: {...}
INFO: Processing callback from <chat_id>: digest_settings_tracked
INFO: Digest mode changed to tracked for user <user_id> (chat_id: <chat_id>)
```

### Шаг 3: Проверка в базе данных

Подключитесь к БД через Railway CLI:

```bash
railway connect postgres
```

Проверьте текущий режим:

```sql
SELECT 
    telegram_chat_id,
    telegram_digest_mode,
    telegram_enabled
FROM user_preferences
WHERE telegram_chat_id = '1018308084';
```

Ожидаемый результат после теста:
- Для `digest_settings_all`: `telegram_digest_mode = 'all'`
- Для `digest_settings_tracked`: `telegram_digest_mode = 'tracked'`

### Шаг 4: Проверка в Telegram боте

1. Откройте Telegram бота
2. Отправьте `/digest` или нажмите "⚙️ Digest Settings"
3. Проверьте, что текущий режим соответствует последнему тесту

## Диагностика проблем

### Проблема: Скрипт возвращает ошибку

**Возможные причины:**

1. **Webhook URL недоступен:**
   ```bash
   curl "https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook"
   ```
   Должен вернуть `{"status": "ok", ...}`

2. **Неправильный chat_id:**
   - Проверьте, что chat_id существует в БД
   - Убедитесь, что `telegram_enabled = true`

3. **Сетевые проблемы:**
   - Проверьте интернет-соединение
   - Убедитесь, что Railway сервис работает

**Решение:**
```bash
# Проверить статус сервисов Railway
railway status

# Проверить пользователя в БД
python -m scripts.check_telegram_user 1018308084
```

### Проблема: Callback отправлен, но не обрабатывается

**Что проверить:**

1. **Логи не показывают обработку:**
   ```bash
   railway logs --service "web" --since 5m | grep -i "callback\|error"
   ```

2. **Пользователь не найден:**
   - Проверьте, что chat_id правильный
   - Убедитесь, что `telegram_enabled = true`

3. **Ошибки в обработке:**
   - Ищите строки с `ERROR` в логах
   - Проверьте, что БД доступна

**Решение:**
```bash
# Проверить пользователя
railway connect postgres
# Затем выполните SQL из RAILWAY_CLI_DIAGNOSTICS.md

# Проверить логи на ошибки
railway logs --service "web" --since 10m | grep -i error
```

### Проблема: Режим не меняется в БД

**Что проверить:**

1. **Транзакция не коммитится:**
   - Проверьте логи на ошибки коммита
   - Убедитесь, что БД доступна

2. **Кеш не очищается:**
   - Код должен автоматически очищать кеш
   - Проверьте, что `db.expire_all()` вызывается

**Решение:**
```sql
-- Проверить текущий режим
SELECT telegram_digest_mode, telegram_enabled
FROM user_preferences
WHERE telegram_chat_id = '1018308084';

-- Вручную обновить (если нужно)
UPDATE user_preferences
SET telegram_digest_mode = 'all'  -- или 'tracked'
WHERE telegram_chat_id = '1018308084';
```

## Полный пример тестирования

```bash
# 1. Проверить пользователя
python -m scripts.check_telegram_user 1018308084

# 2. Тестировать кнопку "All News"
python -m scripts.test_telegram_buttons_railway \
  --chat-id 1018308084 \
  --button digest_settings_all

# 3. Проверить логи
railway logs --service "web" --since 2m | grep -i "digest_settings_all"

# 4. Проверить в БД
railway connect postgres
# Затем в psql:
SELECT telegram_digest_mode FROM user_preferences WHERE telegram_chat_id = '1018308084';

# 5. Тестировать кнопку "Tracked Only"
python -m scripts.test_telegram_buttons_railway \
  --chat-id 1018308084 \
  --button digest_settings_tracked

# 6. Снова проверить
SELECT telegram_digest_mode FROM user_preferences WHERE telegram_chat_id = '1018308084';
```

## Связанные файлы

- `backend/scripts/test_telegram_buttons_railway.py` - основной скрипт
- `backend/app/api/v1/endpoints/telegram.py` - обработка webhook и callback
- `backend/app/services/telegram_service.py` - отправка сообщений в Telegram
- `backend/RAILWAY_CLI_DIAGNOSTICS.md` - диагностика через Railway CLI
- `backend/scripts/check_telegram_user.py` - проверка настроек пользователя

## Примечания

- Скрипт симулирует callback запросы, но не отправляет сообщения в Telegram
- Для полной проверки работы кнопок проверьте также Telegram бота вручную
- Рекомендуется тестировать на проде после проверки в dev окружении
- Скрипт создает уникальные `callback_id` на основе timestamp для избежания конфликтов

















