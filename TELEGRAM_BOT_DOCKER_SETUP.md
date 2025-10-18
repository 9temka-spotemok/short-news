# 🤖 Telegram Bot Docker Setup

Полная настройка Telegram бота в Docker контейнере для проекта AI Competitor Insight Hub.

## 📋 Что создано

### Docker файлы
- `backend/Dockerfile.bot` - Docker образ для Telegram бота
- Обновлен `docker-compose.yml` с сервисом `telegram-bot`

### Скрипты управления
- `backend/scripts/run_telegram_bot.py` - Скрипт запуска бота в контейнере
- `backend/scripts/docker_bot_management.sh` - Управление для Linux/macOS
- `backend/scripts/docker_bot_management.ps1` - Управление для Windows

### Документация
- `backend/TELEGRAM_BOT_DOCKER_README.md` - Подробная документация

## 🚀 Быстрый запуск

### 1. Настройка бота

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

### 3. Проверка работы

```bash
# Проверить статус
docker-compose ps telegram-bot

# Посмотреть логи
docker-compose logs -f telegram-bot
```

## 🛠️ Управление (Linux/macOS)

```bash
# Сделать скрипт исполняемым
chmod +x backend/scripts/docker_bot_management.sh

# Команды управления
./backend/scripts/docker_bot_management.sh start    # Запустить
./backend/scripts/docker_bot_management.sh stop     # Остановить
./backend/scripts/docker_bot_management.sh restart  # Перезапустить
./backend/scripts/docker_bot_management.sh logs     # Логи
./backend/scripts/docker_bot_management.sh status   # Статус
./backend/scripts/docker_bot_management.sh health   # Проверка здоровья
./backend/scripts/docker_bot_management.sh shell    # Shell в контейнере
```

## 🛠️ Управление (Windows)

```powershell
# Команды управления
.\backend\scripts\docker_bot_management.ps1 start    # Запустить
.\backend\scripts\docker_bot_management.ps1 stop     # Остановить
.\backend\scripts\docker_bot_management.ps1 restart  # Перезапустить
.\backend\scripts\docker_bot_management.ps1 logs     # Логи
.\backend\scripts\docker_bot_management.ps1 status   # Статус
.\backend\scripts\docker_bot_management.ps1 health   # Проверка здоровья
.\backend\scripts\docker_bot_management.ps1 shell    # Shell в контейнере
```

## 🔧 Прямые команды Docker

```bash
# Основные команды
docker-compose up -d telegram-bot          # Запуск
docker-compose stop telegram-bot           # Остановка
docker-compose restart telegram-bot        # Перезапуск
docker-compose logs -f telegram-bot        # Логи
docker-compose ps telegram-bot             # Статус
docker-compose build telegram-bot          # Сборка

# Отладка
docker exec -it shot-news-telegram-bot /bin/bash  # Shell
```

## 📊 Архитектура контейнера

### Особенности
- ✅ **Polling режим** - получает обновления от Telegram API
- ✅ **Health Check** - автоматическая проверка здоровья
- ✅ **Graceful Shutdown** - корректное завершение работы
- ✅ **Логирование** - подробные логи работы
- ✅ **Безопасность** - запуск от непривилегированного пользователя
- ✅ **Автоперезапуск** - `restart: unless-stopped`

### Переменные окружения
- `TELEGRAM_BOT_TOKEN` - Токен бота (обязательно)
- `DATABASE_URL` - Подключение к PostgreSQL
- `REDIS_URL` - Подключение к Redis
- `FRONTEND_*_URL` - URL фронтенда для кнопок

### Volumes
- `./backend:/app` - Монтирование кода
- `bot_logs:/var/log` - Логи бота

## 🔍 Мониторинг

### Health Check
Контейнер автоматически проверяет:
- Подключение к Telegram API
- Доступность базы данных
- Доступность Redis

### Логи
```bash
# Просмотр логов
docker-compose logs -f telegram-bot

# Последние 100 строк
docker-compose logs --tail=100 telegram-bot

# Логи за период
docker-compose logs --since="1h" telegram-bot
```

### Проверка здоровья
```bash
# Через скрипт
./backend/scripts/docker_bot_management.sh health

# Прямая проверка API
docker exec shot-news-telegram-bot python -c "
import requests, os
token = os.getenv('TELEGRAM_BOT_TOKEN')
print(requests.get(f'https://api.telegram.org/bot{token}/getMe').json())
"
```

## 🐛 Troubleshooting

### Частые проблемы

1. **Bot token не настроен**
   ```bash
   # Решение
   cd backend
   python setup_telegram_bot_interactive.py
   ```

2. **База данных недоступна**
   ```bash
   # Проверить статус PostgreSQL
   docker-compose ps postgres
   
   # Перезапустить все сервисы
   docker-compose down && docker-compose up -d
   ```

3. **Конфликт webhook**
   ```bash
   # Удалить webhook через API
   curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
   ```

4. **Контейнер не запускается**
   ```bash
   # Проверить логи
   docker-compose logs telegram-bot
   
   # Пересобрать образ
   docker-compose build telegram-bot
   ```

## 📝 Команды бота

После запуска бот поддерживает следующие команды:

- `/start` - Приветствие и получение Chat ID
- `/help` - Список команд
- `/digest` - Получение дайджеста
- `/settings` - Просмотр настроек
- `/subscribe` - Подписка на дайджесты
- `/unsubscribe` - Отписка от дайджестов

## 🔄 Обновление

```bash
# Обновить код
git pull

# Пересобрать и перезапустить
docker-compose build telegram-bot
docker-compose up -d telegram-bot
```

## 📚 Дополнительная документация

Подробная документация доступна в файле:
- `backend/TELEGRAM_BOT_DOCKER_README.md`

---

**🎉 Готово!** Telegram бот теперь запускается в Docker контейнере с полной интеграцией в систему дайджестов.

