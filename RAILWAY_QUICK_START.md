# ⚡ Быстрый деплой на Railway

## 🚀 Экспресс-деплой (10 минут)

### 1. Подготовка
- ✅ Проект уже готов (`railway.json` создан)
- ✅ Переменные окружения подготовлены (`backend/env.production`)

### 2. Создание проекта на Railway
1. Зайдите на [railway.app](https://railway.app)
2. "New Project" → "Deploy from GitHub repo"
3. Выберите репозиторий `short-news`
4. **ВАЖНО:** В Settings → Root Directory измените с `/` на `/backend`

### 3. Добавление сервисов
1. **PostgreSQL:** "+ New" → "Database" → "PostgreSQL"
2. **Redis:** "+ New" → "Database" → "Redis"

### 4. Настройка переменных
В Railway Dashboard → Variables добавьте:

```bash
# Обязательные
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key-here
FRONTEND_BASE_URL=https://your-app-name.netlify.app
FRONTEND_SETTINGS_URL=https://your-app-name.netlify.app/settings
FRONTEND_DIGEST_SETTINGS_URL=https://your-app-name.netlify.app/settings/digest
ALLOWED_HOSTS=["https://your-app-name.netlify.app"]

# API ключи
OPENAI_API_KEY=your-openai-api-key
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```

### 5. Деплой
- Railway автоматически начнет деплой
- Дождитесь завершения (2-5 минут)
- Получите URL бэкенда

### 6. Обновление фронтенда
В Netlify добавьте переменную:
```
VITE_API_URL = https://your-backend-url.railway.app
```

## ✅ Проверка
- Health: `https://your-backend-url.railway.app/api/v1/health`
- API docs: `https://your-backend-url.railway.app/docs`
- Фронтенд работает без ошибок

## 🆘 Быстрая помощь
- **Ошибка сборки:** Проверьте логи в Railway
- **CORS ошибки:** Проверьте `ALLOWED_HOSTS`
- **База данных:** Проверьте `DATABASE_URL`

---

**🎉 Готово! Проект работает на Railway!**
