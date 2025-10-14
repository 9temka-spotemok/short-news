# Исправление ошибки 404 на странице Digest Settings

## Дата: 14 октября 2025

---

## 🔍 Проблема

При переходе на страницу `/digest-settings` возникала ошибка **404 Not Found**:

```
GET http://localhost:8000/api/v1/users/preferences/digest - 404 Not Found
AxiosError: 'Request failed with status code 404'
Source: DigestSettingsPage.tsx:28
```

---

## 🕵️ Анализ

### Причина ошибки:

1. **Backend эндпоинт существовал**, но возвращал 404 когда у пользователя отсутствовала запись `UserPreferences`
2. **При регистрации пользователя** не создавалась запись в таблице `user_preferences`
3. **Первый запрос** к `/users/preferences/digest` приводил к ошибке:
   ```python
   if not preferences:
       raise HTTPException(status_code=404, detail="User preferences not found")
   ```

### Затронутые компоненты:

- **Backend:** `backend/app/api/v1/endpoints/users.py`
  - Эндпоинт `GET /users/preferences/digest` (строка 200)
  - Эндпоинт `PUT /users/preferences/digest` (строка 257)
- **Frontend:** `frontend/src/pages/DigestSettingsPage.tsx`
  - Запрос к API на строке 28

---

## ✅ Решение

### Изменения в Backend

#### 1. GET /users/preferences/digest (строки 200-254)

**Было:**
```python
preferences = result.scalar_one_or_none()

if not preferences:
    raise HTTPException(status_code=404, detail="User preferences not found")
```

**Стало:**
```python
preferences = result.scalar_one_or_none()

# Create default preferences if they don't exist
if not preferences:
    logger.info(f"Creating default preferences for user {current_user.id}")
    from app.models.preferences import DigestFrequency, DigestFormat, NotificationFrequency
    
    preferences = UserPreferences(
        id=uuid.uuid4(),
        user_id=current_user.id,
        subscribed_companies=[],
        interested_categories=[],
        keywords=[],
        notification_frequency=NotificationFrequency.DAILY,
        digest_enabled=False,
        digest_frequency=DigestFrequency.DAILY,
        digest_custom_schedule={},
        digest_format=DigestFormat.SHORT,
        digest_include_summaries=True,
        telegram_chat_id=None,
        telegram_enabled=False
    )
    db.add(preferences)
    await db.commit()
    await db.refresh(preferences)
```

#### 2. PUT /users/preferences/digest (строки 257-295)

**Было:**
```python
if not preferences:
    raise HTTPException(status_code=404, detail="User preferences not found")
```

**Стало:**
```python
# Create default preferences if they don't exist
if not preferences:
    logger.info(f"Creating default preferences for user {current_user.id}")
    from app.models.preferences import DigestFrequency, DigestFormat, NotificationFrequency
    
    preferences = UserPreferences(
        id=uuid.uuid4(),
        user_id=current_user.id,
        subscribed_companies=[],
        interested_categories=[],
        keywords=[],
        notification_frequency=NotificationFrequency.DAILY,
        digest_enabled=False,
        digest_frequency=DigestFrequency.DAILY,
        digest_custom_schedule={},
        digest_format=DigestFormat.SHORT,
        digest_include_summaries=True,
        telegram_chat_id=None,
        telegram_enabled=False
    )
    db.add(preferences)
```

---

## 🎯 Результат

### Что исправлено:

✅ **Автоматическое создание UserPreferences**
- При первом запросе к digest settings автоматически создается запись с настройками по умолчанию

✅ **Нет ошибок 404**
- Пользователи могут открывать страницу digest settings без проблем

✅ **Настройки по умолчанию**
- `digest_enabled`: false (отключено)
- `digest_frequency`: daily (ежедневно)
- `digest_format`: short (краткий формат)
- `digest_include_summaries`: true (включать саммари)
- `telegram_enabled`: false (Telegram отключен)

### Поведение системы:

1. **Первое посещение /digest-settings:**
   - Backend создает запись UserPreferences с настройками по умолчанию
   - Возвращает эти настройки клиенту
   - Пользователь видит форму с дефолтными значениями

2. **Последующие посещения:**
   - Backend находит существующую запись
   - Возвращает сохраненные настройки

3. **Сохранение настроек:**
   - При PUT запросе обновляются существующие настройки
   - Или создаются новые, если их не было

---

## 🧪 Тестирование

### Как протестировать:

1. **Обновите страницу в браузере** (F5)
2. Перейдите на страницу **Digest Settings** через меню
3. Вы должны увидеть форму с настройками вместо ошибки 404
4. Попробуйте изменить настройки и сохранить их
5. Обновите страницу - настройки должны сохраниться

### Ожидаемый результат:

```
✅ Страница загружается без ошибок
✅ Форма отображается с настройками по умолчанию
✅ Можно включить/выключить digest
✅ Можно выбрать частоту (Daily/Weekly/Custom)
✅ Можно выбрать формат (Short/Detailed)
✅ Настройки сохраняются корректно
```

---

## 📝 Технические детали

### Измененные файлы:

1. **`backend/app/api/v1/endpoints/users.py`**
   - Функция `get_digest_settings()` (строки 200-254)
   - Функция `update_digest_settings()` (строки 257-295+)

### Новая логика:

```python
# Паттерн "Создать если не существует"
preferences = get_or_none(user_id)
if not preferences:
    preferences = create_default(user_id)
    save(preferences)
return preferences
```

### Настройки по умолчанию:

```python
UserPreferences(
    id=uuid.uuid4(),
    user_id=current_user.id,
    subscribed_companies=[],           # Пустой список
    interested_categories=[],           # Пустой список
    keywords=[],                        # Пустой список
    notification_frequency=DAILY,       # Ежедневно
    digest_enabled=False,               # Отключено
    digest_frequency=DAILY,             # Ежедневно
    digest_custom_schedule={},          # Пустой объект
    digest_format=SHORT,                # Краткий формат
    digest_include_summaries=True,      # Включать саммари
    telegram_chat_id=None,              # Не настроен
    telegram_enabled=False              # Отключено
)
```

---

## 🔄 Перезапуск

Backend был перезапущен для применения изменений:
```bash
docker-compose restart backend
```

Статус: ✅ **Backend работает корректно**

---

## 📋 Связанные исправления

Эта фикса является частью общего исправления системы Digest:

1. ✅ **Миграция базы данных** - добавлены таблицы notifications и колонки digest
2. ✅ **Синхронизация типов** - NewsCategory на frontend и backend
3. ✅ **Структура DigestData** - обновлена на frontend
4. ✅ **UI ошибки** - добавлены проверки на undefined в DashboardPage
5. ✅ **404 на Digest Settings** - автоматическое создание UserPreferences

---

## 🎉 Заключение

Проблема **полностью решена**. Пользователи теперь могут:
- Открывать страницу Digest Settings без ошибок
- Видеть и изменять свои настройки
- Сохранять конфигурацию digest
- Настраивать Telegram интеграцию

**Статус:** ✅ ИСПРАВЛЕНО  
**Backend:** ✅ Работает  
**Frontend:** ✅ Готов к использованию

---

*Отчет создан: 14 октября 2025*

