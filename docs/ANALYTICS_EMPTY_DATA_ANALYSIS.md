# Анализ проблемы пустых данных аналитики

## 🐛 Проблема

Фронтенд получает:
- ✅ `/analytics/graph` → `[]` (пустой массив)
- ✅ `/analytics/companies/{id}/snapshots` → `{snapshots: []}` (пустой массив)
- ❌ `/analytics/companies/{id}/impact/latest` → `404 (Not Found)`

## 🔍 Причины

### 1. Пустой массив snapshots

**Эндпоинт:** `GET /api/v2/analytics/companies/{company_id}/snapshots`

**Код:**
```222:235:backend/app/api/v2/endpoints/analytics.py
async def get_company_snapshots(
    company_id: UUID,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAILY),
    limit: int = Query(default=30, ge=1, le=180),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsFacade = Depends(get_analytics_facade),
) -> SnapshotSeriesResponse:
    snapshots = await analytics.get_snapshots(company_id, period, limit)
    snapshot_models = [_snapshot_to_response(snapshot) for snapshot in snapshots]
    return SnapshotSeriesResponse(
        company_id=company_id,
        period=period,
        snapshots=snapshot_models,
    )
```

**Причина:** Для компании нет snapshots в БД.

**Решение:**
1. Запустить пересчет аналитики: `POST /api/v2/analytics/companies/{id}/recompute?period=daily&lookback=30`
2. Или дождаться автоматического создания при запросе `/impact/latest`

### 2. 404 на `/impact/latest`

**Эндпоинт:** `GET /api/v2/analytics/companies/{company_id}/impact/latest`

**Логика:**
1. Ищет последний snapshot для компании и периода
2. Если не найден → пытается создать автоматически
3. Если создание не удалось → создает пустой snapshot
4. Если пустой snapshot не удалось создать → возвращает 404

**Возможные причины 404:**

#### 2.1. Ошибка при вычислении snapshot (`compute_snapshot_for_period`)

**Признаки в логах:**
```
ERROR: Failed to auto-create snapshot for company ...: ...
INFO: compute_snapshot_for_period failed, creating empty snapshot as fallback...
```

**Возможные причины:**
- ❌ Нет данных для вычисления (нет новостей, событий)
- ❌ Ошибка в SQL запросе при агрегации
- ❌ Ошибка в логике вычисления метрик

**Проверка:**
```sql
-- Проверить новости для компании
SELECT COUNT(*) FROM news_items 
WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe';

-- Проверить события
SELECT COUNT(*) FROM competitor_change_events 
WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe';
```

#### 2.2. Ошибка при сохранении пустого snapshot

**Признаки в логах:**
```
ERROR: Failed to create empty snapshot for company ...: ...
# Затем выбрасывается HTTPException с 404
```

**Возможные причины:**
- ❌ Нарушение UniqueConstraint (дубликат snapshot)
- ❌ Проблемы с foreign key (company_id не существует)
- ❌ Проблемы с типом данных
- ❌ Проблемы с транзакцией БД

**Проверка:**
```sql
-- Проверить существование компании
SELECT id, name FROM companies 
WHERE id = '75eee989-a419-4220-bdc6-810c4854a1fe';

-- Проверить существующие snapshots для периода
SELECT id, period_start, period 
FROM company_analytics_snapshots 
WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe' 
  AND period = 'daily'
ORDER BY period_start DESC;
```

### 3. Пустой массив graph edges

**Эндпоинт:** `GET /api/v2/analytics/graph`

**Код:**
```360:369:backend/app/api/v2/endpoints/analytics.py
stmt = select(AnalyticsGraphEdge).order_by(AnalyticsGraphEdge.created_at.desc()).limit(limit)

if company_id:
    stmt = stmt.where(AnalyticsGraphEdge.company_id == company_id)
if relationship:
    stmt = stmt.where(AnalyticsGraphEdge.relationship_type == relationship)

result = await db.execute(stmt)
edges = list(result.scalars().all())
return [_edge_to_response(edge) for edge in edges]
```

**Причина:** В БД нет графовых ребер для компании.

**Решение:**
1. Граф создается при вызове `sync_knowledge_graph`
2. Это происходит либо автоматически, либо через задачу Celery
3. Для создания графа нужны новости и события для компании

## 🔧 Диагностика

### Шаг 1: Проверить логи сервера

При запросе `/impact/latest` должны быть логи:

```
INFO: get_latest_snapshot called: company_id=..., period=daily, user_id=...
INFO: Calling analytics.get_latest_snapshot(company_id=..., period=daily)
DEBUG: SnapshotService.get_latest_snapshot: company_id=..., period=AnalyticsPeriod.DAILY (value=daily)
DEBUG: Executing SQL query for get_latest_snapshot...
INFO: SnapshotService.get_latest_snapshot result: NOT FOUND (id=None)
INFO: get_latest_snapshot result: snapshot=NOT FOUND (id=None)
INFO: Snapshot not found, attempting to create automatically...
INFO: Computing snapshot for period_start=..., period=daily
```

Если есть ошибки:
```
ERROR: Failed to auto-create snapshot for company ...: ...
ERROR: Failed to create empty snapshot for company ...: ...
```

### Шаг 2: Запустить пересчет аналитики

```bash
curl -X POST "http://localhost:8000/api/v2/analytics/companies/75eee989-a419-4220-bdc6-810c4854a1fe/recompute?period=daily&lookback=30" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Шаг 3: Проверить данные в БД

1. Проверить существование компании
2. Проверить наличие новостей для компании
3. Проверить наличие событий для компании
4. Проверить существующие snapshots

## ✅ Решения

### Решение 1: Запустить пересчет аналитики

Самое простое решение - запустить пересчет аналитики через API:

```bash
POST /api/v2/analytics/companies/{company_id}/recompute?period=daily&lookback=30
```

Это создаст snapshots для последних 30 дней.

### Решение 2: Проверить логи на ошибки

Если пересчет не помогает, проверить логи сервера на конкретные ошибки при создании snapshot.

### Решение 3: Проверить данные в БД

Убедиться, что:
- Компания существует
- Есть новости для компании
- Есть события для компании (опционально)

## 📊 Файлы системы

1. **Эндпоинт:** `backend/app/api/v2/endpoints/analytics.py`
   - `get_latest_snapshot()` - получение последнего snapshot
   - `get_company_snapshots()` - получение списка snapshots
   - `get_graph_edges()` - получение графовых ребер

2. **Сервис:** `backend/app/domains/analytics/services/snapshot_service.py`
   - `get_latest_snapshot()` - поиск последнего snapshot
   - `compute_snapshot_for_period()` - вычисление snapshot
   - `refresh_company_snapshots()` - пересчет snapshots

3. **Фасад:** `backend/app/domains/analytics/facade.py`
   - `AnalyticsFacade` - точка входа для операций

## 🎯 Следующие шаги

1. ✅ Проверить логи сервера при запросе `/impact/latest`
2. ✅ Запустить пересчет аналитики для компании
3. ✅ Проверить данные в БД (компания, новости, события)
4. ✅ Если ошибки остаются - исправить проблему на основе логов




