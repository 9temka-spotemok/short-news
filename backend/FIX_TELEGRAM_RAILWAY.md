# Исправление Telegram бота на Railway

## Проблема
Локально работает контейнер `shot-news-telegram-bot` (polling режим), но на Railway нет отдельного Telegram сервиса, поэтому бот не работает.

## Решение: Настроить Webhook режим (Рекомендуется)

Webhook режим лучше для production - не нужно держать отдельный сервис для polling.

### Шаг 1: Проверить, что webhook endpoint доступен

```bash
# Проверка через GET (health check)
curl "https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook"
```

Должен вернуть:
```json
{
  "status": "ok",
  "message": "Telegram webhook endpoint is active...",
  "method": "POST"
}
```

### Шаг 2: Установить webhook в Telegram

**Способ A: Через ваш API endpoint**

```bash
curl "https://web-production-6bf5.up.railway.app/api/v1/telegram/set-webhook?webhook_url=https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook"
```

**Способ B: Через Telegram API напрямую**

```bash
curl "https://api.telegram.org/bot<ВАШ_BOT_TOKEN>/setWebhook?url=https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook"
```

**Способ C: Через Python скрипт**

```bash
cd backend
python setup_telegram_webhook.py setup
```

Когда попросит URL, введите:
```
https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook
```

### Шаг 3: Проверить статус webhook

```bash
curl "https://web-production-6bf5.up.railway.app/api/v1/telegram/get-webhook-info"
```

Или через Telegram API:
```bash
curl "https://api.telegram.org/bot<ВАШ_BOT_TOKEN>/getWebhookInfo"
```

Ожидаемый результат:
```json
{
  "status": "success",
  "webhook_info": {
    "url": "https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

### Шаг 4: Протестировать

1. Откройте Telegram бота
2. Отправьте `/start`
3. Нажмите кнопку "📅 Daily Digest"
4. Проверьте логи:
   ```bash
   railway logs --service "web" --since 1m | grep -i "webhook\|callback"
   ```

Должны увидеть:
```
INFO: Received Telegram webhook: {...}
INFO: Processing callback from <chat_id>: digest_daily
```

---

## Альтернатива: Добавить Telegram сервис на Railway (Polling режим)

Если хотите использовать polling режим как локально:

### Шаг 1: Добавить сервис на Railway

1. В Railway Dashboard: ваш проект → **+ New** → **GitHub Repo**
2. Выберите тот же репозиторий
3. Railway автоматически определит конфигурацию из `railway-telegram.json`

### Шаг 2: Настроить переменные окружения

В новом Telegram сервисе установите те же переменные, что и в `web`:
- `DATABASE_URL`
- `REDIS_URL`
- `TELEGRAM_BOT_TOKEN`
- `SECRET_KEY`
- И другие необходимые переменные

### Шаг 3: Убедиться, что webhook удален

Если ранее был установлен webhook, удалите его:
```bash
curl "https://api.telegram.org/bot<ВАШ_BOT_TOKEN>/deleteWebhook"
```

Polling и Webhook не могут работать одновременно!

---

## Какой вариант выбрать?

### Webhook (рекомендуется):
✅ Не нужен отдельный сервис  
✅ Меньше ресурсов  
✅ Быстрее (нет задержки polling)  
✅ Лучше для production  

### Polling:
✅ Проще для разработки  
✅ Не нужен публичный URL  
❌ Требует отдельный сервис  
❌ Постоянное использование ресурсов  

---

## Проверка работы после настройки

### Для Webhook:
1. `railway logs --service "web" --follow`
2. Нажмите кнопку в Telegram
3. Должны увидеть: `Received Telegram webhook`

### Для Polling:
1. `railway logs --service "telegram" --follow`
2. Нажмите кнопку в Telegram
3. Должны увидеть: `Received message from ...` или `Received callback from ...`



















