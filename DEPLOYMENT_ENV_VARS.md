# Инструкции по настройке переменных окружения в Netlify

## Переменные окружения для фронтенда в Netlify

1. Войдите в панель управления Netlify
2. Выберите ваш сайт
3. Перейдите в Site settings > Environment variables
4. Добавьте следующие переменные:

### Обязательные переменные:
- `VITE_API_URL` = `https://your-backend-api.com` (замените на URL вашего бэкенда)

### Дополнительные переменные (опционально):
- `VITE_APP_NAME` = `AI Competitor Insight Hub`
- `VITE_APP_VERSION` = `0.1.0`

## Переменные окружения для бэкенда

### Для Railway.app:
1. Войдите в Railway dashboard
2. Выберите ваш проект
3. Перейдите в Variables
4. Добавьте переменные из файла `backend/env.production`

### Для Render.com:
1. Войдите в Render dashboard
2. Выберите ваш сервис
3. Перейдите в Environment
4. Добавьте переменные из файла `backend/env.production`

### Для Heroku:
1. Войдите в Heroku dashboard
2. Выберите ваше приложение
3. Перейдите в Settings > Config Vars
4. Добавьте переменные из файла `backend/env.production`

## Важные замечания:

1. **SECRET_KEY**: Обязательно измените на уникальный секретный ключ для продакшена
2. **DATABASE_URL**: Используйте внешний PostgreSQL (например, Supabase, Neon, или Railway PostgreSQL)
3. **REDIS_URL**: Используйте внешний Redis (например, Upstash, Redis Cloud, или Railway Redis)
4. **ALLOWED_HOSTS**: Добавьте ваш Netlify домен в список разрешенных хостов
5. **FRONTEND_*_URL**: Обновите URL фронтенда на ваш Netlify домен

## Пример настройки для продакшена:

```bash
# Frontend (Netlify)
VITE_API_URL=https://shot-news-backend.railway.app

# Backend (Railway/Render/Heroku)
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-production-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
REDIS_URL=redis://user:pass@host:port
ALLOWED_HOSTS=["https://shot-news.netlify.app"]
FRONTEND_BASE_URL=https://shot-news.netlify.app
FRONTEND_SETTINGS_URL=https://shot-news.netlify.app/settings
FRONTEND_DIGEST_SETTINGS_URL=https://shot-news.netlify.app/settings/digest
```
