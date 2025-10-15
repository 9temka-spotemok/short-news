# Исправление ошибки 500 в /api/v1/notifications/unread

## 🔴 Проблема

```
GET http://localhost:8000/api/v1/notifications/unread 500 (Internal Server Error)
Error fetching notifications: AxiosError
```

## 🎯 Решение (2 шага)

### Шаг 1: Примените миграцию

Откройте **новый терминал PowerShell** в директории проекта и выполните:

```powershell
cd C:\Users\priah\Desktop\short-news\backend
python -m alembic upgrade head
```

**Ожидаемый вывод:**
```
INFO  [alembic.runtime.migration] Running upgrade ... -> c1d2e3f4g5h6, add_digest_and_notifications
```

Если увидите эту строку - миграция применена ✅

### Шаг 2: Создайте настройки пользователей

В том же терминале:

```powershell
python scripts\init_all_settings.py
```

**Ожидаемый вывод:**
```
INFO - Created X user preferences
INFO - Created X notification settings
```

### Шаг 3: Перезапустите backend

1. Остановите backend (Ctrl+C в терминале где он запущен)
2. Запустите снова:

```powershell
cd C:\Users\priah\Desktop\short-news\backend
python -m uvicorn main:app --reload
```

### Шаг 4: Обновите браузер

1. Откройте страницу заново (F5)
2. Ошибка должна исчезнуть

---

## 🔍 Проверка что всё работает

### Проверка 1: Swagger UI

Откройте:
```
http://localhost:8000/docs
```

1. Нажмите "Authorize"
2. Введите ваш access token
3. Найдите endpoint `GET /api/v1/notifications/unread`
4. Нажмите "Try it out" → "Execute"

**Ожидается:**
```json
{
  "unread_count": 0,
  "notifications": []
}
```

Статус: **200 OK** ✅

### Проверка 2: Frontend

Откройте:
```
http://localhost:5173
```

1. Войдите в систему
2. Посмотрите на Header - должна быть иконка колокольчика
3. Кликните на колокольчик
4. Должен открыться dropdown "No new notifications"

**Не должно быть:**
- ❌ Ошибок в консоли
- ❌ 500 Internal Server Error

---

## ❓ Что делает миграция

Создает 3 новые таблицы:

1. **`notifications`** - хранит уведомления
   - id, user_id, type, title, message, data
   - is_read, priority, created_at, read_at

2. **`notification_settings`** - настройки уведомлений
   - id, user_id, enabled
   - notification_types, min_priority_score
   - company_alerts, category_trends, keyword_alerts

3. **`competitor_comparisons`** - сравнения конкурентов
   - id, user_id, name
   - company_ids, date_from, date_to, metrics

4. Добавляет поля в **`user_preferences`**:
   - digest_enabled, digest_frequency
   - digest_custom_schedule, digest_format
   - digest_include_summaries
   - telegram_chat_id, telegram_enabled

---

## 🐛 Если миграция не применяется

### Ошибка: "Target database is not up to date"

```powershell
cd backend
python -m alembic current
# Посмотрите какая версия

# Если не c1d2e3f4g5h6:
python -m alembic upgrade head
```

### Ошибка: "relation notifications does not exist"

Миграция не применилась. Проверьте:

```powershell
# Подключитесь к PostgreSQL
docker exec -it short-news-postgres-1 psql -U postgres -d short_news

# Проверьте таблицы
\dt

# Должны быть:
# notifications
# notification_settings
# competitor_comparisons
```

Если их нет:
```powershell
cd backend
python -m alembic upgrade head --sql > migration.sql
# Проверьте файл migration.sql - там должны быть CREATE TABLE
```

### Ошибка: "Can't locate revision"

Очистите кеш:
```powershell
cd backend
Remove-Item alembic\versions\__pycache__ -Recurse -Force
python -m alembic upgrade head
```

---

## 🚀 Альтернативный метод (если миграция уже применена)

Если миграция уже применена, но ошибка всё равно есть:

### Создайте настройки вручную через SQL:

1. Подключитесь к БД:
```powershell
docker exec -it short-news-postgres-1 psql -U postgres -d short_news
```

2. Проверьте пользователей:
```sql
SELECT id, email FROM users;
```

3. Для каждого user_id создайте настройки:
```sql
-- Замените YOUR_USER_ID на ID из предыдущей команды
INSERT INTO notification_settings (
    id, user_id, enabled, notification_types, 
    min_priority_score, company_alerts, category_trends, keyword_alerts,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'YOUR_USER_ID',
    true,
    '{}',
    0,
    true,
    true,
    true,
    NOW(),
    NOW()
);
```

4. Проверьте:
```sql
SELECT * FROM notification_settings;
```

---

## ✅ После исправления

1. ✅ Backend запускается без ошибок
2. ✅ GET /api/v1/notifications/unread возвращает 200
3. ✅ Frontend колокольчик работает
4. ✅ Нет ошибок в консоли браузера
5. ✅ Можно открыть /notifications
6. ✅ Можно открыть /digest-settings
7. ✅ Можно открыть /competitor-analysis

Всё должно работать! 🎉

---

## 📞 Если проблема остается

Соберите информацию:

1. Вывод команды:
```powershell
cd backend
python -m alembic current
```

2. Последние строки логов backend (где запущен uvicorn)

3. Полный текст ошибки из консоли браузера (F12)

4. Вывод команды:
```powershell
docker exec -it short-news-postgres-1 psql -U postgres -d short_news -c "\dt"
```

Это поможет точно определить проблему!



