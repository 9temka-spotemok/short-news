# Статус парсеров для Pricing страниц

## ✅ Парсеры реализованы и работают!

### Что есть:

1. **PricingPageParser** (`backend/app/parsers/pricing.py`)
   - ✅ Парсит HTML pricing страниц
   - ✅ Извлекает планы, цены, features
   - ✅ Поддерживает множественные форматы (карточки, таблицы)
   - ✅ Версия: `2025.11.0`

2. **CompetitorIngestionDomainService** (`backend/app/domains/competitors/services/ingestion_service.py`)
   - ✅ Координирует парсинг pricing страниц
   - ✅ Создаёт pricing snapshots
   - ✅ Вычисляет diff между snapshots
   - ✅ Создаёт change events при обнаружении изменений

3. **Celery задача** (`backend/app/tasks/competitors.py`)
   - ✅ `ingest_pricing_page` - асинхронный парсинг
   - ✅ Автоматическая загрузка HTML если не передан
   - ✅ Retry логика при ошибках

4. **API endpoints** (`backend/app/api/v1/endpoints/competitors.py`)
   - ✅ `GET /changes/{company_id}` - получить change events
   - ✅ `POST /changes/{event_id}/recompute` - пересчитать event
   - ❌ **НЕТ endpoint для запуска парсинга** (нужно создать)

---

## 🔍 Как работает парсинг

### Процесс:

1. **Парсинг HTML:**
   ```python
   parser = PricingPageParser()
   result = parser.parse(html, url=source_url)
   # result.plans - список планов с ценами и features
   ```

2. **Создание snapshot:**
   ```python
   snapshot = await snapshot_repo.create_snapshot(
       company_id=company_id,
       normalized_data=normalized_plans,
       data_hash=hash,
       ...
   )
   ```

3. **Сравнение с предыдущим:**
   ```python
   previous_snapshot = await snapshot_repo.fetch_latest(company_id, source_url)
   diff = compute_diff(previous_data, normalized_plans)
   ```

4. **Создание change event:**
   ```python
   if has_changes(diff):
       event = await change_service.create_change_event(
           company_id=company_id,
           diff=diff,
           ...
       )
   ```

---

## 📊 Текущее состояние

| Компонент | Статус | Примечание |
|-----------|--------|------------|
| **PricingPageParser** | ✅ Работает | Версия 2025.11.0 |
| **IngestionService** | ✅ Работает | Готов к использованию |
| **Celery задача** | ✅ Работает | `ingest_pricing_page` |
| **API endpoint** | ❌ Отсутствует | Нужно создать |
| **Pricing Snapshots** | 0 | Не парсились страницы |
| **Change Events** | 0 | Нет snapshots для сравнения |

---

## 🚀 Как запустить парсинг

### Вариант 1: Через Celery задачу (рекомендуется)

```python
from app.tasks.competitors import ingest_pricing_page

# Запустить парсинг
task = ingest_pricing_page.delay(
    company_id="75eee989-a419-4220-bdc6-810c4854a1fe",
    source_url="https://snowseo.com/pricing",
    source_type="news_site"
)

# Проверить статус
print(f"Task ID: {task.id}")
```

### Вариант 2: Напрямую через сервис

```python
from app.domains.competitors import CompetitorFacade
from app.core.database import AsyncSessionLocal
from app.models import SourceType

async with AsyncSessionLocal() as session:
    facade = CompetitorFacade(session)
    event = await facade.ingest_pricing_page(
        company_id=UUID("75eee989-a419-4220-bdc6-810c4854a1fe"),
        source_url="https://snowseo.com/pricing",
        html=None,  # будет загружен автоматически
        source_type=SourceType.NEWS_SITE
    )
    print(f"Change event created: {event.id}")
```

### Вариант 3: Создать API endpoint

Нужно добавить в `backend/app/api/v1/endpoints/competitors.py`:

```python
@router.post("/ingest-pricing")
async def ingest_pricing_page_endpoint(
    request_data: dict = Body(...),
    current_user: User = Depends(get_current_user),
):
    """Запустить парсинг pricing страницы"""
    from app.tasks.competitors import ingest_pricing_page
    from app.models import SourceType
    
    company_id = request_data.get("company_id")
    source_url = request_data.get("source_url")
    source_type = SourceType(request_data.get("source_type", "news_site"))
    
    task = ingest_pricing_page.delay(
        company_id=company_id,
        source_url=source_url,
        source_type=source_type.value
    )
    
    return {"status": "queued", "task_id": task.id}
```

---

## ✅ Вывод

**Парсеры ЕСТЬ и работают!** 

Проблема не в отсутствии парсеров, а в том, что:
1. ❌ Нет API endpoint для запуска парсинга (можно создать)
2. ⚠️ Парсинг не запускался автоматически для компаний
3. ⚠️ Нужно вручную запустить парсинг pricing страниц

**После запуска парсинга:**
- Создадутся pricing snapshots
- При обнаружении изменений создадутся change events
- Change events появятся в аналитике и добавят компоненты "Pricing Changes" и "Feature Updates" в Impact Score

---

## 🎯 Рекомендации

1. **Создать API endpoint** для запуска парсинга pricing страниц
2. **Добавить автоматический парсинг** при добавлении компании (если есть pricing URL)
3. **Настроить периодический парсинг** через Celery Beat для отслеживания изменений




