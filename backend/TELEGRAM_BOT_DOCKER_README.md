# Telegram Bot Docker Container

Этот документ описывает как запустить Telegram бота в Docker контейнере.

## Структура файлов

- `Dockerfile.bot` - Docker образ для Telegram бота
- `scripts/run_telegram_bot.py` - Скрипт запуска бота в контейнере
- `scripts/docker_bot_management.sh` - Скрипт управления контейнером (Linux/macOS)
- `scripts/docker_bot_management.ps1` - Скрипт управления контейнером (Windows)

## Быстрый старт

### 1. Настройка бота

Сначала настройте бота с помощью интерактивного скрипта:

```bash
cd backend
python setup_telegram_bot_interactive.py
```

### 2. Запуск через Docker Compose

```bash
# Запустить только бота
docker-compose up -d telegram-bot

# Запустить все сервисы включая бота
docker-compose up -d
```

### 3. Проверка статуса

```bash
# Проверить статус контейнера
docker-compose ps telegram-bot

# Посмотреть логи
docker-compose logs -f telegram-bot
```

## Управление контейнером

### Linux/macOS

Используйте скрипт `scripts/docker_bot_management.sh`:

```bash
# Сделать скрипт исполняемым
chmod +x backend/scripts/docker_bot_management.sh

# Команды управления
./backend/scripts/docker_bot_management.sh start    # Запустить бота
./backend/scripts/docker_bot_management.sh stop     # Остановить бота
./backend/scripts/docker_bot_management.sh restart  # Перезапустить бота
./backend/scripts/docker_bot_management.sh logs     # Показать логи
./backend/scripts/docker_bot_management.sh status   # Показать статус
./backend/scripts/docker_bot_management.sh health   # Проверить здоровье
./backend/scripts/docker_bot_management.sh shell    # Открыть shell в контейнере
./backend/scripts/docker_bot_management.sh build    # Собрать образ
./backend/scripts/docker_bot_management.sh clean    # Очистить контейнеры
```

### Windows

Используйте PowerShell скрипт `scripts/docker_bot_management.ps1`:

```powershell
# Команды управления
.\backend\scripts\docker_bot_management.ps1 start    # Запустить бота
.\backend\scripts\docker_bot_management.ps1 stop     # Остановить бота
.\backend\scripts\docker_bot_management.ps1 restart  # Перезапустить бота
.\backend\scripts\docker_bot_management.ps1 logs     # Показать логи
.\backend\scripts\docker_bot_management.ps1 status   # Показать статус
.\backend\scripts\docker_bot_management.ps1 health   # Проверить здоровье
.\backend\scripts\docker_bot_management.ps1 shell    # Открыть shell в контейнере
.\backend\scripts\docker_bot_management.ps1 build    # Собрать образ
.\backend\scripts\docker_bot_management.ps1 clean    # Очистить контейнеры
```

### Прямые команды Docker

```bash
# Запуск
docker-compose up -d telegram-bot

# Остановка
docker-compose stop telegram-bot

# Перезапуск
docker-compose restart telegram-bot

# Логи
docker-compose logs -f telegram-bot

# Статус
docker-compose ps telegram-bot

# Shell в контейнере
docker exec -it shot-news-telegram-bot /bin/bash

# Сборка образа
docker-compose build telegram-bot
```

## Конфигурация

### Переменные окружения

Контейнер бота использует следующие переменные окружения:

- `TELEGRAM_BOT_TOKEN` - Токен Telegram бота (обязательно)
- `DATABASE_URL` - URL базы данных PostgreSQL
- `REDIS_URL` - URL Redis для кеша и очередей
- `CELERY_BROKER_URL` - URL брокера Celery
- `CELERY_RESULT_BACKEND` - URL бэкенда результатов Celery
- `FRONTEND_BASE_URL` - Базовый URL фронтенда
- `FRONTEND_SETTINGS_URL` - URL страницы настроек
- `FRONTEND_DIGEST_SETTINGS_URL` - URL страницы настроек дайджестов
- `ENVIRONMENT` - Окружение (development/staging/production)
- `DEBUG` - Режим отладки
- `SECRET_KEY` - Секретный ключ

### Volumes

- `./backend:/app` - Монтирование кода приложения
- `bot_logs:/var/log` - Логи бота

## Мониторинг и отладка

### Health Check

Контейнер включает встроенную проверку здоровья, которая:

1. Проверяет доступность Telegram API
2. Проверяет подключение к базе данных
3. Проверяет подключение к Redis

### Логи

```bash
# Показать логи в реальном времени
docker-compose logs -f telegram-bot

# Показать последние 100 строк логов
docker-compose logs --tail=100 telegram-bot

# Показать логи за определенный период
docker-compose logs --since="2024-01-01T00:00:00" telegram-bot
```

### Отладка

```bash
# Открыть shell в контейнере
docker exec -it shot-news-telegram-bot /bin/bash

# Проверить переменные окружения
docker exec shot-news-telegram-bot env | grep TELEGRAM

# Проверить процессы в контейнере
docker exec shot-news-telegram-bot ps aux

# Проверить подключение к базе данных
docker exec shot-news-telegram-bot python -c "from app.core.database import AsyncSessionLocal; print('DB OK')"
```

## Архитектура

### Компоненты

1. **TelegramPolling** - Основной класс для polling Telegram API
2. **TelegramService** - Сервис для отправки сообщений
3. **Handlers** - Обработчики команд и сообщений
4. **Database Integration** - Интеграция с базой данных для пользователей
5. **Celery Integration** - Интеграция с Celery для фоновых задач

### Поток данных

1. Telegram API → Polling → Handlers → Database
2. User Commands → Handlers → TelegramService → Telegram API
3. Digest Generation → Celery → TelegramService → Telegram API

## Безопасность

- Контейнер запускается от непривилегированного пользователя `botuser`
- Все секреты передаются через переменные окружения
- Health check не раскрывает чувствительную информацию
- Логи не содержат токенов или паролей

## Производительность

- Использует async/await для неблокирующих операций
- Polling с таймаутом 30 секунд для эффективного использования ресурсов
- Автоматическое переподключение при ошибках
- Graceful shutdown при получении сигналов

## Troubleshooting

### Частые проблемы

1. **Bot token не настроен**
   ```
   Error: TELEGRAM_BOT_TOKEN not configured
   ```
   Решение: Запустите `python setup_telegram_bot_interactive.py`

2. **База данных недоступна**
   ```
   Error: Dependencies not ready
   ```
   Решение: Убедитесь, что PostgreSQL контейнер запущен и здоров

3. **Redis недоступен**
   ```
   Error: Redis connection failed
   ```
   Решение: Убедитесь, что Redis контейнер запущен и здоров

4. **Webhook конфликт**
   ```
   Error: Conflict with webhook
   ```
   Решение: Удалите webhook через Telegram API или используйте polling

### Логи для отладки

```bash
# Включить debug режим
docker-compose up -d telegram-bot
docker exec shot-news-telegram-bot printenv DEBUG
# Должно быть: true

# Проверить подключение к Telegram API
docker exec shot-news-telegram-bot python -c "
import requests
import os
token = os.getenv('TELEGRAM_BOT_TOKEN')
response = requests.get(f'https://api.telegram.org/bot{token}/getMe')
print(response.json())
"
```

## Разработка

### Локальная разработка

```bash
# Запустить в режиме разработки с hot reload
docker-compose up telegram-bot

# Или запустить локально без Docker
cd backend
python scripts/telegram_polling.py
```

### Тестирование

```bash
# Тест отправки сообщения
docker exec shot-news-telegram-bot python -c "
from app.services.telegram_service import telegram_service
import asyncio
asyncio.run(telegram_service.send_digest('YOUR_CHAT_ID', 'Test message'))
"
```

## Обновление

```bash
# Обновить код
git pull

# Пересобрать и перезапустить
docker-compose build telegram-bot
docker-compose up -d telegram-bot
```
