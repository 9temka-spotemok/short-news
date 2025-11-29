# Система здоровья источников (Source Health Service)

## 📋 Обзор

`SourceHealthService` отслеживает состояние источников новостей и автоматически отключает неработающие URL, чтобы предотвратить ненужные HTTP-запросы и улучшить производительность scraper'а.

## 🎯 Цель

- **Сокращение HTTP-запросов на 60-80%** за счёт исключения неработающих URL
- **Автоматическое отключение** URL, которые возвращают 404/410 или пустые ответы
- **Восстановление** URL, которые снова начинают работать

## 🔧 Как это работает

### 1. Хранение данных

Информация о здоровье источников хранится в `SourceProfile.metadata_json['dead_urls']`:

```json
{
  "normalized_url": {
    "status": "disabled" | "recovering" | "healthy",
    "fail_count": 5,
    "last_error": "404 Not Found" | "Empty response",
    "disabled_until": "2025-01-20T12:00:00Z" | null,
    "permanent": true | false,
    "last_success": "2025-01-15T10:00:00Z"
  }
}
```

### 2. Логика отключения

#### Постоянные ошибки (404/410)
- **Порог:** 5 неудачных попыток подряд
- **Действие:** URL отключается **навсегда** (`permanent: true`, `disabled_until: null`)
- **Восстановление:** Автоматически, если URL снова начинает возвращать контент

#### Временные проблемы (пустые ответы)
- **Порог:** 5 неудачных попыток подряд
- **Действие:** URL отключается **временно** на 24 часа (`permanent: false`, `disabled_until: <дата>`)
- **Восстановление:** Автоматически через 24 часа или при успешном ответе

### 3. Нормализация URL

Все URL нормализуются перед сохранением:
- Убирается trailing slash (`/blog` и `/blog/` → одинаковые)
- Домен приводится к lowercase
- Убираются query params для сравнения

## 📊 API

### `get_dead_urls(company_id: UUID) -> Set[str]`

Возвращает множество отключенных URL для компании, которые нужно пропустить при scraping.

**Использование:**
```python
from app.domains.news.services.source_health_service import SourceHealthService

async with AsyncSessionLocal() as db:
    health_service = SourceHealthService(db)
    dead_urls = await health_service.get_dead_urls(company_id)
    # dead_urls = {"https://example.com/blog", "https://example.com/news"}
```

### `record_result(...)`

Записывает результат попытки получения данных из источника.

**Параметры:**
- `company_id`: UUID компании
- `source_url`: URL источника (будет нормализован)
- `success`: Успешность запроса (bool)
- `status`: HTTP статус код (int)
- `items_count`: Количество найденных статей (int)
- `source_type`: Тип источника (SourceType, опционально)

**Использование:**
```python
await health_service.record_result(
    company_id=company_id,
    source_url="https://example.com/blog",
    success=False,
    status=404,
    items_count=0,
    source_type=SourceType.BLOG,
)
```

### `should_skip_url(company_id: UUID, source_url: str) -> bool`

Проверяет, нужно ли пропустить URL.

**Использование:**
```python
if await health_service.should_skip_url(company_id, url):
    logger.info(f"Skipping disabled URL: {url}")
    continue
```

## 🔍 Диагностика

### Проверка отключенных URL для компании

```sql
SELECT 
    company_id,
    source_type,
    metadata_json->'dead_urls' as dead_urls
FROM source_profiles
WHERE company_id = 'YOUR_COMPANY_ID'::uuid
  AND metadata_json->'dead_urls' IS NOT NULL;
```

### Подсчёт отключенных URL

```sql
SELECT 
    company_id,
    source_type,
    jsonb_object_keys(metadata_json->'dead_urls') as disabled_url
FROM source_profiles
WHERE metadata_json->'dead_urls' IS NOT NULL
  AND jsonb_typeof(metadata_json->'dead_urls') = 'object';
```

### Проверка статуса конкретного URL

```sql
SELECT 
    company_id,
    source_type,
    metadata_json->'dead_urls'->'https://example.com/blog' as url_status
FROM source_profiles
WHERE metadata_json->'dead_urls'->'https://example.com/blog' IS NOT NULL;
```

### Поиск URL с постоянным отключением

```sql
SELECT 
    company_id,
    source_type,
    key as disabled_url,
    value->>'status' as status,
    value->>'permanent' as permanent,
    value->>'fail_count' as fail_count
FROM source_profiles,
     jsonb_each(metadata_json->'dead_urls')
WHERE value->>'status' = 'disabled'
  AND (value->>'permanent')::boolean = true;
```

## 🔄 Переинициализация источника

Если URL был отключен по ошибке или источник восстановился, можно переинициализировать:

### Вариант 1: Удалить запись вручную

```sql
UPDATE source_profiles
SET metadata_json = jsonb_set(
    metadata_json,
    '{dead_urls}',
    (metadata_json->'dead_urls') - 'https://example.com/blog'
)
WHERE company_id = 'YOUR_COMPANY_ID'::uuid
  AND metadata_json->'dead_urls'->'https://example.com/blog' IS NOT NULL;
```

### Вариант 2: Запустить первичное сканирование

```python
from app.tasks.scraping import scan_company_sources_initial

# Запустить задачу для компании
scan_company_sources_initial.delay(str(company_id))
```

Эта задача проверит все возможные URL и обновит статусы в `SourceHealthService`.

## 📈 Метрики

Система экспортирует метрики в Prometheus:

- `scraper_dead_urls_count{company_id="..."}` — количество отключенных URL для компании (gauge)
- `scraper_requests_total{status="404", source_type="blog"}` — общее количество запросов по статусу (counter)
- `scraper_duplicate_requests_total{source_type="blog"}` — количество предотвращённых дубликатов (counter)

## 🚀 Интеграция

### В scraper'е

`UniversalBlogScraper` автоматически использует `SourceHealthService`:

```python
# При scraping компании
skip_urls = await health_service.get_dead_urls(company.id)
items = await scraper.scrape_company_blog(
    company_name=company.name,
    website=company.website,
    skip_urls=skip_urls,  # Автоматически пропускаются отключенные URL
    company_id=company.id,
    health_service=health_service,
)

# После каждого запроса
await health_service.record_result(
    company_id=company.id,
    source_url=url,
    success=success,
    status=status_code,
    items_count=items_count,
    source_type=SourceType.BLOG,
)
```

### Первичная инициализация

При создании новой компании автоматически запускается задача `scan_company_sources_initial`, которая:
1. Проверяет все возможные URL источников
2. Записывает результаты в `SourceHealthService`
3. Отключает неработающие URL сразу

## ⚙️ Настройки

Параметры можно изменить в `SourceHealthService`:

```python
FAIL_THRESHOLD = 5  # Количество неудачных попыток перед отключением
DISABLE_DURATION_HOURS = 24  # Часы для временного отключения (только для пустых ответов)
```

## 🔍 Логирование

Система логирует важные события:

- `URL {url} permanently disabled (404/410) for company {company_id}` — постоянное отключение
- `URL {url} temporarily disabled (empty response) for company {company_id}` — временное отключение
- `URL {url} succeeded, resetting fail count for company {company_id}` — успешное восстановление

## 📝 Примеры использования

### Проверка здоровья источников компании

```python
from app.domains.news.services.source_health_service import SourceHealthService
from app.core.database import AsyncSessionLocal

async with AsyncSessionLocal() as db:
    health_service = SourceHealthService(db)
    dead_urls = await health_service.get_dead_urls(company_id)
    
    print(f"Отключено URL: {len(dead_urls)}")
    for url in dead_urls:
        print(f"  - {url}")
```

### Ручная запись результата

```python
await health_service.record_result(
    company_id=company_id,
    source_url="https://example.com/blog",
    success=True,
    status=200,
    items_count=5,
    source_type=SourceType.BLOG,
)
```

## 🐛 Решение проблем

### URL не отключается

1. Проверьте, что `record_result` вызывается после каждого запроса
2. Убедитесь, что `fail_count` достигает порога (5)
3. Проверьте логи на наличие ошибок

### URL отключён, но должен работать

1. Проверьте статус в БД (см. SQL запросы выше)
2. Удалите запись вручную или запустите первичное сканирование
3. При следующем scraping URL будет проверен снова

### Слишком много отключённых URL

1. Проверьте метрику `scraper_dead_urls_count`
2. Проверьте логи на наличие проблем с сетью
3. Рассмотрите возможность увеличения `FAIL_THRESHOLD`

---

**Последнее обновление:** 2025-01-19  
**Файл:** `backend/app/domains/news/services/source_health_service.py`

