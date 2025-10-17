# 🐳 News Scraper Container

Отдельный Docker контейнер для автоматического поиска и сбора новостей.

## 📋 Описание

Контейнер `news-scraper` автоматически запускает скрапинг новостей каждый час и сохраняет результаты в базу данных.

## ⏰ Расписание

- **Каждый час**: Запуск `scrape_all_companies.py` (в 00 минут каждого часа)
- **Каждые 6 часов**: Запуск `populate_news.py` (в 00:00, 06:00, 12:00, 18:00)
- **Еженедельно**: Очистка старых логов (каждое воскресенье в 02:00)

## 🚀 Запуск

### Запуск всех сервисов (включая скрапер):
```bash
docker-compose up -d
```

### Запуск только скрапера:
```bash
docker-compose up news-scraper -d
```

### Одноразовый запуск скрапера:
```bash
docker-compose run --rm news-scraper /usr/local/bin/run-scraper.sh
```

## 📊 Мониторинг

### Просмотр логов скрапера:
```bash
# Логи контейнера
docker-compose logs -f news-scraper

# Логи скрапинга
docker-compose exec news-scraper tail -f /var/log/scraper.log
```

### Проверка статуса cron:
```bash
docker-compose exec news-scraper crontab -l
```

### Проверка процессов:
```bash
docker-compose exec news-scraper ps aux | grep cron
```

## 🔧 Управление

### Остановка скрапера:
```bash
docker-compose stop news-scraper
```

### Перезапуск скрапера:
```bash
docker-compose restart news-scraper
```

### Пересборка контейнера:
```bash
docker-compose build news-scraper
docker-compose up news-scraper -d
```

## 📁 Структура файлов

```
backend/
├── Dockerfile.scraper          # Dockerfile для контейнера скрапера
├── scripts/
│   ├── scraper-entrypoint.sh   # Entrypoint скрипт
│   ├── scraper-cron           # Конфигурация cron jobs
│   ├── run-scraper.sh         # Скрипт для запуска скрапера
│   └── scrape_all_companies.py # Основной скрипт скрапинга
```

## 🐛 Отладка

### Проверка подключения к БД:
```bash
docker-compose exec news-scraper python -c "
import asyncio
from app.core.database import AsyncSessionLocal

async def test_db():
    async with AsyncSessionLocal() as db:
        await db.execute('SELECT 1')
    print('✅ Database connection OK')

asyncio.run(test_db())
"
```

### Ручной запуск скрапера:
```bash
docker-compose exec news-scraper python scripts/scrape_all_companies.py
```

### Проверка cron jobs:
```bash
docker-compose exec news-scraper cat /etc/cron.d/scraper-cron
```

## 📈 Производительность

- Контейнер использует минимальные ресурсы
- Автоматический перезапуск при сбоях (`restart: unless-stopped`)
- Health check для мониторинга состояния
- Логирование всех операций

## 🔒 Безопасность

- Контейнер работает с теми же переменными окружения, что и основной backend
- Доступ к базе данных только для чтения/записи новостей
- Изолированная среда выполнения

## 📝 Логи

Все логи сохраняются в:
- `/var/log/scraper.log` - внутри контейнера
- `docker-compose logs news-scraper` - логи Docker

Формат логов:
```
2024-01-15 10:00:01: Starting scheduled news scraping...
2024-01-15 10:00:02: Running scrape_all_companies.py...
2024-01-15 10:05:30: ✅ scrape_all_companies.py completed successfully
2024-01-15 10:05:31: Scheduled scraping completed successfully
```



