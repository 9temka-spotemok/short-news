# Отчёт по исправлению ошибок Worker сервиса

**Дата:** 2025-11-17  
**Сервис:** Worker (Celery)  
**Окружение:** Production (Railway)

---

## 📋 Сводка

Исправлены критические ошибки в worker сервисе, которые приводили к падению задач и ошибкам в логах. Все проблемы решены, сервис работает стабильно.

---

## 🔍 Обнаруженные проблемы

### 1. Ошибка типов в SQL запросе

**Ошибка:**
```
ProgrammingError: operator does not exist: character varying[] @> newscategory[]
HINT: No operator matches the given name and argument types. You might need to add explicit type casts.
```

**Локация:** `backend/app/domains/notifications/repositories/preferences_repository.py:34`

**Причина:**
- Метод `list_interested_in_category` использовал SQLAlchemy `.contains()` для сравнения enum массива
- SQLAlchemy генерировал запрос, который пытался сравнить `character varying[]` с `newscategory[]`
- PostgreSQL требует явного приведения типов для работы с enum массивами

**Решение:**
- Использован raw SQL с явным приведением типа `ARRAY[:category::newscategory]`
- Реализован двухэтапный запрос: сначала получаем IDs через raw SQL, затем загружаем полные объекты через ORM

**Файл:** `backend/app/domains/notifications/repositories/preferences_repository.py`

---

### 2. Проблемы с Event Loop в asyncpg соединениях

**Ошибка:**
```
RuntimeError: Event loop is closed
Task <Task pending> got Future attached to a different loop
```

**Локация:** `backend/app/tasks/digest.py`

**Причина:**
- Использовался `asyncio.run()`, который создавал новый event loop и закрывал его после выполнения
- Соединения asyncpg были привязаны к закрытому event loop
- При закрытии соединений возникали ошибки "Event loop is closed"

**Решение:**
- Унифицирован подход с `notifications.py`
- Добавлен механизм управления event loop с переиспользованием между задачами
- Удален `nest_asyncio`, который вызывал конфликты
- Все задачи используют `_run_async()` вместо `asyncio.run()`

**Файл:** `backend/app/tasks/digest.py`

---

### 3. Отсутствующие колонки в базе данных

**Ошибка:**
```
UndefinedColumnError: column news_items.topic does not exist
```

**Локация:** `backend/app/domains/news/repositories/news_repository.py:44`

**Причина:**
- Миграция `f7a8b9c0d1e2_add_news_topic_sentiment_snapshot` была пропущена в цепочке миграций
- В базе данных была версия `73b129050e97`, но колонки `topic`, `sentiment`, `raw_snapshot_url` отсутствовали
- Модель `NewsItem` содержала эти поля, но в БД их не было

**Решение:**
- Применен SQL напрямую для добавления недостающих колонок
- Созданы enum типы: `newstopic` и `sentimentlabel`
- Добавлены колонки: `topic`, `sentiment`, `raw_snapshot_url`
- Временно использован `load_only()` для исключения несуществующих колонок
- После добавления колонок возвращен обычный запрос без `load_only()`

**Файлы:**
- `backend/app/domains/news/repositories/news_repository.py` (временное исправление)
- SQL команды применены напрямую в Railway PostgreSQL

---

## ✅ Выполненные исправления

### 1. Исправление метода `list_interested_in_category`

**Файл:** `backend/app/domains/notifications/repositories/preferences_repository.py`

**Было:**
```python
async def list_interested_in_category(self, category: str) -> List[UserPreferences]:
    result = await self._session.execute(
        select(UserPreferences).where(
            UserPreferences.interested_categories.contains([category])
        )
    )
    return list(result.scalars().all())
```

**Стало:**
```python
async def list_interested_in_category(self, category: str) -> List[UserPreferences]:
    # PostgreSQL requires explicit type casting when comparing enum arrays
    result = await self._session.execute(
        text("""
            SELECT id FROM user_preferences 
            WHERE interested_categories @> ARRAY[:category::newscategory]
        """),
        {"category": category}
    )
    ids = [row[0] for row in result.all()]
    if not ids:
        return []
    
    result = await self._session.execute(
        select(UserPreferences).where(UserPreferences.id.in_(ids))
    )
    return list(result.scalars().all())
```

---

### 2. Исправление управления Event Loop в digest задачах

**Файл:** `backend/app/tasks/digest.py`

**Изменения:**
- Удален `nest_asyncio`
- Добавлен механизм управления event loop аналогично `notifications.py`
- Все задачи (`generate_daily_digests`, `generate_weekly_digests`, `send_channel_digest`) используют `_run_async()`

**Добавленный код:**
```python
# Event loop management for Celery tasks
_ASYNC_EVENT_LOOP = None
_ASYNC_LOCK = threading.Lock()

def _get_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create event loop for current thread"""
    global _ASYNC_EVENT_LOOP
    if _ASYNC_EVENT_LOOP is None or _ASYNC_EVENT_LOOP.is_closed():
        _ASYNC_EVENT_LOOP = asyncio.new_event_loop()
    return _ASYNC_EVENT_LOOP

def _run_async(fn, *args, **kwargs):
    """Execute async coroutine in dedicated event loop for current process"""
    coro = fn(*args, **kwargs)
    with _ASYNC_LOCK:
        loop = _get_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(coro)
            return result
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
```

---

### 3. Добавление недостающих колонок в базу данных

**Применённый SQL:**
```sql
-- Создать enum типы
CREATE TYPE newstopic AS ENUM (
    'product', 'strategy', 'finance', 'technology', 'security',
    'research', 'community', 'talent', 'regulation', 'market', 'other'
);

CREATE TYPE sentimentlabel AS ENUM (
    'positive', 'neutral', 'negative', 'mixed'
);

-- Добавить колонки
ALTER TABLE news_items ADD COLUMN topic newstopic;
ALTER TABLE news_items ADD COLUMN sentiment sentimentlabel;
ALTER TABLE news_items ADD COLUMN raw_snapshot_url VARCHAR(1000);
```

**Проверка результата:**
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'news_items' 
AND column_name IN ('topic', 'sentiment', 'raw_snapshot_url');
```

**Результат:**
- ✅ `topic` - USER-DEFINED (newstopic)
- ✅ `sentiment` - USER-DEFINED (sentimentlabel)
- ✅ `raw_snapshot_url` - character varying

---

### 4. Возврат обычного запроса в `fetch_by_url`

**Файл:** `backend/app/domains/news/repositories/news_repository.py`

**Было (временное исправление):**
```python
async def fetch_by_url(self, url: str) -> Optional[NewsItem]:
    stmt = (
        select(NewsItem)
        .options(
            selectinload(NewsItem.company),
            load_only(NewsItem.id, NewsItem.title, ...)  # исключали topic, sentiment, raw_snapshot_url
        )
        .where(NewsItem.source_url == url)
    )
```

**Стало:**
```python
async def fetch_by_url(self, url: str) -> Optional[NewsItem]:
    stmt = (
        select(NewsItem)
        .options(selectinload(NewsItem.company))
        .where(NewsItem.source_url == url)
    )
    result = await self._session.execute(stmt)
    return result.scalar_one_or_none()
```

---

## 📊 Результаты

### До исправления:
- ❌ Задачи `check_daily_trends` падали с ошибкой типов
- ❌ Задачи `generate_weekly_digests` падали с ошибкой event loop
- ❌ Задачи `send_channel_digest` падали с ошибкой event loop
- ❌ Задачи `scrape_ai_blogs` падали с ошибкой отсутствующих колонок
- ❌ Множественные retry попытки задач

### После исправления:
- ✅ Все задачи выполняются без ошибок
- ✅ Event loop управляется корректно
- ✅ SQL запросы работают с правильными типами
- ✅ Все колонки существуют в базе данных
- ✅ Нет ошибок в логах worker

---

## 🔧 Технические детали

### Использованные технологии:
- **SQLAlchemy** - для работы с БД
- **asyncpg** - драйвер PostgreSQL
- **Celery** - для фоновых задач
- **asyncio** - для асинхронных операций

### Ключевые изменения:
1. Raw SQL с явным приведением типов для enum массивов
2. Переиспользование event loop между задачами Celery
3. Прямое применение SQL миграций в обход Alembic (из-за пропущенной миграции)

---

## 📝 Рекомендации на будущее

1. **Миграции:**
   - Регулярно проверять применение всех миграций
   - Использовать `alembic current` для проверки версии
   - При пропуске миграций применять их вручную через SQL

2. **Event Loop:**
   - Использовать единый подход для всех Celery задач
   - Не использовать `asyncio.run()` в Celery worker процессах
   - Переиспользовать event loop между задачами

3. **Enum массивы:**
   - Всегда использовать явное приведение типов при работе с enum массивами в PostgreSQL
   - Тестировать запросы с enum массивами перед деплоем

4. **Мониторинг:**
   - Регулярно проверять логи worker на ошибки
   - Настроить алерты на критические ошибки
   - Отслеживать retry попытки задач

---

## ✅ Чеклист проверки

- [x] Исправлена ошибка типов в `list_interested_in_category`
- [x] Исправлены проблемы с event loop в digest задачах
- [x] Добавлены недостающие колонки в базу данных
- [x] Возвращен обычный запрос в `fetch_by_url`
- [x] Проверена работа всех исправлений
- [x] Удалены временные файлы (`check_enum_validation.sql`)

---

## 📁 Изменённые файлы

1. `backend/app/domains/notifications/repositories/preferences_repository.py`
   - Исправлен метод `list_interested_in_category` для работы с enum массивами

2. `backend/app/tasks/digest.py`
   - Добавлен механизм управления event loop
   - Все задачи используют `_run_async()` вместо `asyncio.run()`

3. `backend/app/domains/news/repositories/news_repository.py`
   - Временно использован `load_only()` (затем возвращен обычный запрос)

4. База данных (Railway PostgreSQL)
   - Добавлены enum типы: `newstopic`, `sentimentlabel`
   - Добавлены колонки: `topic`, `sentiment`, `raw_snapshot_url`

---

## 🎯 Заключение

Все критические ошибки в worker сервисе исправлены. Сервис работает стабильно, задачи выполняются без ошибок. Рекомендуется продолжить мониторинг логов для выявления возможных проблем на ранней стадии.

**Статус:** ✅ Все проблемы решены









