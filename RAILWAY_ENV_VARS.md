# Railway Environment Variables

## 🔧 Переменные окружения для Railway

Скопируйте эти переменные в Railway Dashboard → Variables:

### 📋 Обязательные переменные

```bash
# Application
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-production-key-change-this

# Frontend URLs (замените на ваш Netlify домен)
FRONTEND_BASE_URL=https://your-app-name.netlify.app
FRONTEND_SETTINGS_URL=https://your-app-name.netlify.app/settings
FRONTEND_DIGEST_SETTINGS_URL=https://your-app-name.netlify.app/settings/digest

# CORS (добавьте ваш Netlify домен)
ALLOWED_HOSTS=["https://your-app-name.netlify.app"]
```

### 🔑 API ключи (заполните реальными значениями)

```bash
# OpenAI API (обязательно)
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Telegram Bot (обязательно)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
TELEGRAM_CHANNEL_ID=@your_channel_name

# Twitter API (опционально)
TWITTER_API_KEY=your-twitter-api-key
TWITTER_API_SECRET=your-twitter-api-secret
TWITTER_ACCESS_TOKEN=your-twitter-access-token
TWITTER_ACCESS_TOKEN_SECRET=your-twitter-access-token-secret

# GitHub API (опционально)
GITHUB_TOKEN=your-github-token-here

# Reddit API (опционально)
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret

# Email (опционально)
SENDGRID_API_KEY=your-sendgrid-api-key
FROM_EMAIL=noreply@shot-news.com
```

### 🗄️ База данных и Redis

Railway автоматически добавит эти переменные при создании сервисов:
- `DATABASE_URL` - для PostgreSQL
- `REDIS_URL` - для Redis
- `CELERY_BROKER_URL` - для Celery
- `CELERY_RESULT_BACKEND` - для Celery

### ⚙️ Дополнительные настройки

```bash
# Scraping
SCRAPER_USER_AGENT=shot-news-bot/1.0 (+https://shot-news.com/bot)
SCRAPER_DELAY=5.0
SCRAPER_TIMEOUT=30

# Rate Limiting
RATE_LIMIT_REQUESTS=100

# Logging
LOG_LEVEL=INFO
```

## 📝 Как добавить переменные в Railway

1. Зайдите в Railway Dashboard
2. Выберите ваш проект
3. Перейдите в раздел "Variables"
4. Нажмите "New Variable"
5. Добавьте каждую переменную по отдельности

## 🔒 Безопасность

- **SECRET_KEY:** Обязательно измените на уникальный ключ
- **API ключи:** Используйте реальные ключи от сервисов
- **CORS:** Добавьте только ваш Netlify домен

## ✅ Проверка

После добавления всех переменных:
- Railway автоматически перезапустит деплой
- Проверьте логи на наличие ошибок
- Убедитесь, что все сервисы работают

---

**🎯 Скопируйте переменные в Railway Dashboard!**
