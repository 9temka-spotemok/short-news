# Анализ Backend Аналитики

## Структура Backend Аналитики

### 1. Endpoints (`backend/app/api/v2/endpoints/analytics.py`)

#### Основные endpoints:
- `GET /analytics/companies/{company_id}/impact/latest` - получение последнего snapshot
- `GET /analytics/companies/{company_id}/snapshots` - получение серии snapshots
- `POST /analytics/companies/{company_id}/recompute` - запуск пересчета аналитики
- `POST /analytics/companies/{company_id}/graph/sync` - синхронизация knowledge graph
- `GET /analytics/graph` - получение edges knowledge graph
- `GET /analytics/change-log` - получение change events

### 2. Сервисы

#### SnapshotService (`backend/app/domains/analytics/services/snapshot_service.py`)

**Основные методы:**
- `get_latest_snapshot()` - получение последнего snapshot для компании
- `compute_snapshot_for_period()` - вычисление snapshot для периода
- `refresh_company_snapshots()` - пересчет snapshots за lookback периодов
- `sync_knowledge_graph()` - синхронизация knowledge graph edges

**Логика создания snapshot:**
1. Агрегирует новости за период (`_aggregate_news`)
2. Загружает change events за период (`_load_change_events`)
3. Вычисляет метрики:
   - News volume, sentiment, priority
   - Pricing changes, feature updates
   - Funding events
   - Innovation velocity
4. Строит impact components
5. Вычисляет impact score
6. Вычисляет trend delta (сравнение с предыдущим snapshot)

### 3. Celery Tasks (`backend/app/tasks/analytics.py`)

#### Задачи:
- `recompute_company_analytics` - пересчет аналитики для одной компании
- `recompute_all_analytics` - пересчет для всех компаний
- `sync_company_knowledge_graph` - синхронизация knowledge graph

#### Автоматический пересчет:
В `backend/app/celery_app.py` настроена периодическая задача:
```python
"recompute-analytics-daily": {
    "task": "app.tasks.analytics.recompute_all_analytics",
    "schedule": 6 * 60 * 60,  # Каждые 6 часов
    "options": {"queue": "analytics"},
}
```

## Проблемы и Решения

### Проблема 1: Snapshot не создается автоматически

**Причина:** 
- Snapshots создаются только при вызове `refresh_company_snapshots()` через Celery task
- Если задача не запущена или не выполнилась, snapshots не будут созданы

**Решение:**
1. Убедиться, что Celery worker запущен и обрабатывает очередь `analytics`
2. Проверить, что автоматическая задача `recompute-analytics-daily` выполняется
3. Вручную запустить пересчет через API endpoint `/analytics/companies/{id}/recompute`

### Проблема 2: Логика вычисления периодов

**Текущая логика в `refresh_company_snapshots()`:**
```python
anchor = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
for offset in range(lookback):
    period_start = anchor - period_duration * (offset + 1)
```

**Проблема:**
- Anchor устанавливается на текущий час (например, 14:00)
- Периоды вычисляются назад от этого момента
- Это может пропустить самый последний период, если сейчас, например, 14:30

**Рекомендация:**
Использовать более точную логику для определения последнего периода:
```python
# Вычислять периоды от начала текущего дня/недели/месяца
anchor = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
```

### Проблема 3: Требования к данным

**Для создания snapshot нужны:**
1. Новости (`NewsItem`) с `company_id`, `published_at`, `sentiment`, `priority_score`
2. Change events (`CompetitorChangeEvent`) с `company_id`, `detected_at`, `processing_status = SUCCESS`

**Если данных нет:**
- Snapshot все равно создастся, но с нулевыми значениями
- Impact score будет 0 или очень низким
- Это нормальное поведение для новых компаний

### Проблема 4: Knowledge Graph пустой

**Причина:**
- Knowledge graph edges создаются только при вызове `sync_knowledge_graph()`
- Edges создаются на основе связи между change events и news items
- Если нет change events или news items, edges не будут созданы

**Решение:**
1. Убедиться, что есть change events с `processing_status = SUCCESS`
2. Убедиться, что есть news items для компании
3. Запустить синхронизацию через `/analytics/companies/{id}/graph/sync`

## Проверка работоспособности

### 1. Проверить наличие данных

```sql
-- Проверить новости для компании
SELECT COUNT(*) FROM news_items WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe';

-- Проверить change events
SELECT COUNT(*) FROM competitor_change_events 
WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe' 
AND processing_status = 'success';

-- Проверить существующие snapshots
SELECT COUNT(*) FROM company_analytics_snapshots 
WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe';
```

### 2. Проверить Celery

```bash
# Проверить, что worker запущен
celery -A app.celery_app inspect active

# Проверить очередь analytics
celery -A app.celery_app inspect reserved
```

### 3. Запустить пересчет вручную

```bash
# Через API
curl -X POST "http://localhost:8000/api/v2/analytics/companies/75eee989-a419-4220-bdc6-810c4854a1fe/recompute?period=daily&lookback=60" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Рекомендации

1. **Добавить автоматическое создание snapshot при первом запросе:**
   - Если snapshot не найден, автоматически запускать пересчет
   - Или возвращать пустой snapshot с сообщением

2. **Улучшить логику периодов:**
   - Использовать более точное определение последнего периода
   - Учитывать текущее время при вычислении периодов

3. **Добавить мониторинг:**
   - Логировать случаи, когда snapshot не найден
   - Отслеживать успешность автоматических пересчетов

4. **Оптимизировать запросы:**
   - Кэшировать результаты запросов к аналитике
   - Использовать индексы для быстрого поиска snapshots

## Файлы, отвечающие за аналитику

- `backend/app/api/v2/endpoints/analytics.py` - API endpoints
- `backend/app/domains/analytics/facade.py` - Facade для координации сервисов
- `backend/app/domains/analytics/services/snapshot_service.py` - Логика создания snapshots
- `backend/app/domains/analytics/services/comparison_service.py` - Логика сравнения
- `backend/app/tasks/analytics.py` - Celery tasks для пересчета
- `backend/app/models/analytics.py` - Модели данных (CompanyAnalyticsSnapshot, ImpactComponent, AnalyticsGraphEdge)




