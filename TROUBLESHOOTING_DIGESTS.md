# Troubleshooting: Дайджесты и новый функционал

## Проблемы и решения

### ✅ Исправлено: CompetitorAnalysisPage

**Проблема:** Type error с `CompanyMultiSelect`  
**Решение:** Уже исправлено - используется `string[]` вместо `Company[]`

---

## Чек-лист для запуска дайджестов

### 1. ✅ Проверьте миграции базы данных

```bash
cd backend

# Проверить текущую версию
alembic current
# или
python -m alembic current

# Если миграция не применена, запустите:
alembic upgrade head
# или
python -m alembic upgrade head
```

**Ожидаемый результат:** Должна быть миграция `c1d2e3f4g5h6`

**Проверка в БД:**
```sql
-- Проверьте что таблицы созданы
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('notifications', 'notification_settings', 'competitor_comparisons');

-- Проверьте что поля добавлены в user_preferences
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'user_preferences' 
AND column_name LIKE 'digest%';
```

### 2. ✅ Проверьте что backend запущен

```bash
cd backend

# Запустите сервер
uvicorn main:app --reload
# или
python -m uvicorn main:app --reload
```

**Проверка:** Откройте http://localhost:8000/docs  
Должны быть endpoints:
- `/api/v1/digest/daily`
- `/api/v1/digest/weekly`
- `/api/v1/users/preferences/digest`
- `/api/v1/notifications/`
- `/api/v1/competitors/compare`

### 3. ✅ Проверьте авторизацию

**Важно:** Все новые endpoints требуют авторизации!

1. Войдите в систему через `/login`
2. Убедитесь что токен сохранен (проверьте localStorage в DevTools)
3. Попробуйте зайти на `/digest-settings`

**Если получаете 401 Unauthorized:**
- Перелогиньтесь
- Проверьте что токен не истек
- Проверьте консоль браузера на ошибки

### 4. ✅ Тестирование endpoints через Swagger UI

1. Откройте http://localhost:8000/docs
2. Нажмите "Authorize" в правом верхнем углу
3. Введите ваш access token (без "Bearer ")
4. Попробуйте endpoints:

**Тест 1: Получить настройки дайджеста**
```
GET /api/v1/users/preferences/digest
```

**Ожидаемый ответ (если ошибка):**
- 404 = У пользователя нет preferences (нужно создать)
- 401 = Не авторизован
- 200 = Успешно

**Тест 2: Обновить настройки**
```
PUT /api/v1/users/preferences/digest
{
  "digest_enabled": true,
  "digest_frequency": "daily",
  "digest_format": "short"
}
```

### 5. ✅ Проверка UserPreferences

**Проблема:** Endpoint может возвращать 404 если у пользователя нет записи в `user_preferences`

**Решение:** Создайте preferences для пользователя:

```sql
-- Проверьте есть ли preferences
SELECT * FROM user_preferences WHERE user_id = 'YOUR_USER_ID';

-- Если нет, создайте (через SQL или API)
INSERT INTO user_preferences (
    id, user_id, subscribed_companies, interested_categories, 
    keywords, notification_frequency, digest_enabled,
    created_at, updated_at
) VALUES (
    gen_random_uuid(), 
    'YOUR_USER_ID', 
    '{}', 
    '{}', 
    '{}', 
    'daily',
    false,
    NOW(),
    NOW()
);
```

**Или через Python:**
```python
from app.models import UserPreferences
from app.core.database import AsyncSessionLocal
import uuid

async def create_preferences(user_id):
    async with AsyncSessionLocal() as db:
        prefs = UserPreferences(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            subscribed_companies=[],
            interested_categories=[],
            keywords=[],
            notification_frequency='daily',
            digest_enabled=False
        )
        db.add(prefs)
        await db.commit()
```

### 6. ✅ Frontend проверка

**Откройте DevTools Console**

1. Перейдите на `/digest-settings`
2. Откройте Console (F12)
3. Проверьте сетевые запросы (Network tab)

**Ищите:**
- `GET /api/v1/users/preferences/digest` - должен вернуть 200
- Если 404 - создайте preferences (см. п.5)
- Если 401 - перелогиньтесь
- Если CORS error - проверьте backend CORS settings

### 7. ✅ Celery (для автоматических дайджестов)

**Необходимо для:**
- Автоматической генерации дайджестов
- Уведомлений
- Отправки в Telegram

```bash
# Terminal 1: Celery Worker
cd backend
celery -A celery_app worker --loglevel=info
# или
python -m celery -A celery_app worker --loglevel=info

# Terminal 2: Celery Beat (scheduled tasks)
cd backend
celery -A celery_app beat --loglevel=info
# или  
python -m celery -A celery_app beat --loglevel=info
```

**Проверка Redis (нужен для Celery):**
```bash
# Если используете Docker
docker ps | grep redis

# Должен быть запущен на localhost:6379
```

---

## Быстрая диагностика

### Тест 1: Backend работает?
```bash
curl http://localhost:8000/api/v1/companies/
```
Ожидается список компаний

### Тест 2: Auth работает?
```bash
# Замените YOUR_TOKEN
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/users/me
```
Ожидается информация о пользователе

### Тест 3: Digest endpoint работает?
```bash
# Замените YOUR_TOKEN
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/users/preferences/digest
```
Ожидается: 200 с настройками или 404

### Тест 4: Frontend доступен?
```
http://localhost:5173/digest-settings
```
Должна открыться страница (после логина)

---

## Частые ошибки

### ❌ "Failed to load digest settings"
**Причина:** 404 Not Found  
**Решение:** У пользователя нет preferences - создайте их (см. п.5)

### ❌ "Could not validate credentials"
**Причина:** 401 Unauthorized  
**Решение:** Перелогиньтесь, токен истек

### ❌ "Network Error" в консоли
**Причина:** Backend не запущен или CORS  
**Решение:** 
1. Проверьте `uvicorn main:app --reload`
2. Проверьте `ALLOWED_HOSTS` в config.py

### ❌ Telegram бот не отвечает
**Причина:** Webhook/polling не настроен  
**Решение:** Это нормально! Отправка РАБОТАЕТ, прием сообщений требует дополнительной настройки

### ❌ "CompanyMultiSelect type error"
**Причина:** Неправильные типы  
**Решение:** Уже исправлено - используйте `string[]`

---

## Минимальный рабочий пример

```bash
# 1. Backend
cd backend
python -m uvicorn main:app --reload

# 2. Frontend (новый terminal)
cd frontend
npm run dev

# 3. Откройте браузер
http://localhost:5173

# 4. Войдите в систему

# 5. Перейдите на настройки
http://localhost:5173/digest-settings

# 6. Если ошибка 404:
# - Откройте http://localhost:8000/docs
# - Authorize с вашим токеном
# - Попробуйте GET /api/v1/users/preferences
# - Если preferences нет - создайте вручную
```

---

## Следующие шаги если всё работает

1. ✅ Настройте дайджест на `/digest-settings`
2. ✅ Проверьте уведомления - клик на колокольчик в Header
3. ✅ Сравните компании на `/competitor-analysis`
4. ✅ (Опционально) Настройте Telegram бота

---

## Нужна помощь?

**Проверьте логи:**

Backend:
```bash
# В терминале где запущен uvicorn
# Смотрите вывод запросов и ошибок
```

Frontend:
```
Откройте DevTools Console (F12)
Проверьте Network tab для API запросов
```

**Соберите информацию:**
1. URL который не работает
2. Ошибка из консоли браузера
3. Ошибка из логов backend
4. HTTP status code (200, 404, 401, 500?)

Эта информация поможет быстро найти проблему!



