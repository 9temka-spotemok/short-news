# Исправление ошибки "The module celery_app was not found" на Railway

## Проблема
Railway не мог найти модуль `celery_app` при запуске Celery Beat и Worker сервисов:
```
Error: Unable to load celery application.
The module celery_app was not found.
```

## Причина
1. **Неправильные команды запуска** - использовались старые команды `celery -A celery_app` вместо `celery -A app.celery_app`
2. **Неправильная рабочая директория** - команды выполнялись не из директории `backend`
3. **Неправильные импорты в задачах** - все задачи использовали неправильный импорт

## Исправления

### 1. Перемещение файла celery_app.py
```bash
mv backend/celery_app.py backend/app/celery_app.py
```

### 2. Исправление импортов во всех задачах
Изменен импорт с:
```python
from celery_app import celery_app  # ❌ Неправильно
```
на:
```python
from app.celery_app import celery_app  # ✅ Правильно
```

Исправлены файлы:
- `backend/app/tasks/digest.py`
- `backend/app/tasks/scraping.py`
- `backend/app/tasks/notifications.py`
- `backend/app/tasks/nlp.py`

### 3. Обновление конфигураций

#### Procfile
```bash
web: cd backend && python start.py
worker: cd backend && celery -A app.celery_app worker --loglevel=info
beat: cd backend && celery -A app.celery_app beat --loglevel=info
```

#### railway-worker.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "nixpacks"
  },
  "deploy": {
    "startCommand": "cd backend && celery -A app.celery_app worker --loglevel=info --concurrency=4",
    "healthcheckPath": "/api/v1/health",
    "healthcheckTimeout": 300,
    "restartPolicyType": "on_failure",
    "restartPolicyMaxRetries": 3,
    "workingDirectory": "backend"
  }
}
```

#### railway-beat.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "nixpacks"
  },
  "deploy": {
    "startCommand": "cd backend && celery -A app.celery_app beat --loglevel=info --pidfile=/tmp/celerybeat.pid --schedule=/tmp/celerybeat-schedule",
    "healthcheckPath": "/api/v1/health",
    "healthcheckTimeout": 300,
    "restartPolicyType": "on_failure",
    "restartPolicyMaxRetries": 3,
    "workingDirectory": "backend"
  }
}
```

#### docker-compose.yml
```yaml
# Celery Worker
celery-worker:
  command: celery -A app.celery_app worker --loglevel=info

# Celery Beat
celery-beat:
  command: celery -A app.celery_app beat --loglevel=info
```

#### render.yaml
```yaml
# Worker
startCommand: cd backend && celery -A app.celery_app worker --loglevel=info

# Beat
startCommand: cd backend && celery -A app.celery_app beat --loglevel=info
```

### 4. Обновление скрипта запуска
В `backend/start-worker.sh`:
```bash
exec celery -A app.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --prefetch-multiplier=1 \
    --max-tasks-per-child=1000 \
    --max-memory-per-child=200000 \
    --pool=prefork \
    --without-gossip \
    --without-mingle \
    --without-heartbeat
```

## Тестирование

Локальный тест подтвердил, что импорт работает:
```bash
cd backend
export SECRET_KEY=test-key
export DATABASE_URL=sqlite:///test.db
export REDIS_URL=redis://localhost:6379
python -c "from app.celery_app import celery_app; print('✅ Celery app imported successfully')"
```

Результат: `✅ Celery app imported successfully`

## Развертывание на Railway

### Для Beat сервиса:
1. Используйте `railway-beat.json` как конфигурацию
2. Убедитесь, что переменные окружения настроены:
   - `SECRET_KEY`
   - `DATABASE_URL`
   - `REDIS_URL`
   - `CELERY_BROKER_URL`
   - `CELERY_RESULT_BACKEND`

### Для Worker сервиса:
1. Используйте `railway-worker.json` как конфигурацию
2. Убедитесь, что переменные окружения настроены

## Проверка работы

После развертывания проверьте логи:
- Beat должен запускаться без ошибок импорта
- Worker должен запускаться без ошибок импорта
- Все задачи должны быть доступны в расписании

## Ключевые моменты

1. **Рабочая директория** - все команды должны выполняться из `backend/`
2. **Правильный импорт** - используйте `app.celery_app` вместо `celery_app`
3. **Переменные окружения** - убедитесь, что все необходимые переменные настроены
4. **Структура проекта** - `celery_app.py` должен находиться в `backend/app/`

Теперь Celery Beat и Worker должны запускаться без ошибок на Railway!
