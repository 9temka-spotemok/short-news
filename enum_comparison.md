# Расхождения по типам enum newscategory

## 📊 Сравнение определений

### 1. ✅ БАЗА ДАННЫХ (реальное состояние)
**Тип:** `newscategory`  
**Значения:** lowercase
```
product_update
pricing_change
strategic_announcement
technical_update
funding_news
research_paper
community_event
partnership
acquisition
integration
security_update
api_update
model_release
performance_improvement
feature_deprecation
```

### 2. ❌ МИГРАЦИЯ 0001_initial_schema.py (строка 53-58)
**Пытается создать:** `news_category`  
**Значения:** UPPERCASE ❌
```python
CREATE TYPE news_category AS ENUM (
    'PRODUCT_UPDATE', 'PRICING_CHANGE', 'STRATEGIC_ANNOUNCEMENT', 
    'TECHNICAL_UPDATE', 'FUNDING_NEWS', 'RESEARCH_PAPER', 'COMMUNITY_EVENT',
    'PARTNERSHIP', 'ACQUISITION', 'INTEGRATION', 'SECURITY_UPDATE',
    'API_UPDATE', 'MODEL_RELEASE', 'PERFORMANCE_IMPROVEMENT', 'FEATURE_DEPRECATION'
);
```

### 3. ❌ МИГРАЦИЯ 28c9c8f54d42_add_enum_types.py (строка 42)
**Пытается изменить:** с lowercase на UPPERCASE ❌
```python
type_=sa.Enum('PRODUCT_UPDATE', 'PRICING_CHANGE', 'STRATEGIC_ANNOUNCEMENT', 
              'TECHNICAL_UPDATE', 'FUNDING_NEWS', 'RESEARCH_PAPER', 
              'COMMUNITY_EVENT', name='newscategory')
```

### 4. ✅ МОДЕЛЬ Python app/models/news.py (строка 18)
**Определение:** правильное ✅
```python
class NewsCategory(str, enum.Enum):
    PRODUCT_UPDATE = "product_update"  # Имя UPPERCASE, значение lowercase
    PRICING_CHANGE = "pricing_change"
    # ...
```

### 5. ✅ МОДЕЛЬ Python app/models/news.py (строка 135-142)
**SQLAlchemy enum:** правильное ✅
```python
news_category_enum = ENUM(
    'product_update', 'pricing_change', 'strategic_announcement', 
    'technical_update', 'funding_news', 'research_paper', 'community_event',
    'partnership', 'acquisition', 'integration', 'security_update',
    'api_update', 'model_release', 'performance_improvement', 'feature_deprecation',
    name='newscategory',
    create_type=False
)
```

## 🔴 ПРОБЛЕМА И ИСТОРИЯ

### История миграций:

1. **0001_initial_schema.py** (начальная миграция):
   - Создала тип `news_category` с **UPPERCASE** значениями (`'PRODUCT_UPDATE'`)
   - Но в реальной базе этот тип не используется активно

2. **28c9c8f54d42_add_enum_types.py** (попытка рефакторинга):
   - Пыталась **изменить** enum с `news_category` (lowercase) на `newscategory` (UPPERCASE)
   - **Проблема:** В реальной базе уже был создан `newscategory` с **lowercase** значениями
   - Миграция не смогла изменить значения, потому что PostgreSQL не позволяет изменять значения enum напрямую

3. **b5037d3c878c_add_new_news_categories.py** (добавление категорий):
   - Добавляла новые значения в `news_category` со **lowercase** (`'partnership'`, `'acquisition'`, etc.)
   - Это создало расхождение: старый тип `news_category` имеет и UPPERCASE, и lowercase значения

### Текущее состояние в базе данных:

**В базе существует ДВА типа enum:**
- `news_category` (oid: 16478) - старый тип, имеет lowercase значения
- `newscategory` (oid: 16848) - новый тип, имеет lowercase значения

**Используется в таблицах:**
- `news_items.category` → использует `newscategory` (lowercase) ✅
- `user_preferences.interested_categories` → использует `_newscategory` (массив, lowercase) ✅

**Ошибка в логах:**
```
ERROR: invalid input value for enum newscategory: "PRODUCT_UPDATE"
```

**Причина:** 
- В базе данных enum `newscategory` имеет значения **lowercase** (`product_update`)
- Миграции пытаются использовать **UPPERCASE** (`PRODUCT_UPDATE`)
- Когда код пытается использовать `PRODUCT_UPDATE` в запросах к `user_preferences.interested_categories`, PostgreSQL не находит такое значение

**Где возникает ошибка:**
- `backend/app/domains/notifications/repositories/preferences_repository.py:34`
- `backend/app/domains/notifications/services/notification_service.py:201`

## ✅ РЕШЕНИЕ (ВЫПОЛНЕНО)

### Исправленные файлы:

1. ✅ **backend/alembic/versions/0001_initial_schema.py**
   - Изменены enum значения с UPPERCASE на lowercase (строки 54-57, 153)

2. ✅ **backend/alembic/versions/28c9c8f54d42_add_enum_types.py**
   - Изменены enum значения с UPPERCASE на lowercase (строки 42, 94, 168, 219)
   - Исправлены как upgrade, так и downgrade функции

3. ✅ **backend/quick_db_setup.py**
   - Изменены enum значения с UPPERCASE на lowercase (строки 57-60)

4. ✅ **backend/reset_migrations.py**
   - Изменены enum значения с UPPERCASE на lowercase (строки 69-72)

5. ✅ **backend/emergency_db_setup.py**
   - Изменены enum значения с UPPERCASE на lowercase (строки 60-63)

6. ✅ **backend/alembic/versions/73b129050e97_validate_enum_values_lowercase.py**
   - Создана проверочная миграция для валидации enum значений

### Результат:

- Все миграции теперь используют **lowercase** значения (как в реальной базе)
- Код Python уже правильный - использует lowercase значения через `NewsCategory.PRODUCT_UPDATE.value`
- Проверочная миграция поможет выявить проблемы при применении миграций на новых базах

### Что делать дальше:

1. Применить миграции на существующей базе (если нужно):
   ```bash
   cd backend && python -m alembic upgrade head
   ```

2. Проверить, что ошибки исчезли из логов

3. Убедиться, что фильтрация по категориям работает корректно

