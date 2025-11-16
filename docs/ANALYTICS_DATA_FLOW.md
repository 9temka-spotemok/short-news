# Схема формирования данных аналитики

## 📊 Полная цепочка формирования данных

### 1. **Эндпоинт API** - точка входа

**Файл:** `backend/app/api/v2/endpoints/analytics.py`

#### 1.1. GET `/companies/{company_id}/impact/latest`

```90:240:backend/app/api/v2/endpoints/analytics.py
async def get_latest_snapshot(...):
    # 1. Проверка и нормализация period
    period_enum = AnalyticsPeriod(period.lower())
    
    # 2. Поиск существующего snapshot
    snapshot = await analytics.get_latest_snapshot(company_id, period_enum)
    
    # 3. Если не найден - автоматическое создание
    if not snapshot:
        # 3.1. Вычисление периода
        period_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 3.2. Попытка создать snapshot с данными
        snapshot = await analytics.snapshots.compute_snapshot_for_period(...)
        
        # 3.3. Если ошибка - создание пустого snapshot
        # Создание CompanyAnalyticsSnapshot с нулевыми значениями
        
    # 4. Конвертация в response
    response = _snapshot_to_response(snapshot)
    return response
```

**Где формируется:**
- `period_start` - вычисляется в эндпоинте (строки 133-136)
- Пустой snapshot - создается в эндпоинте (строки 187-204)
- Response - формируется через `_snapshot_to_response()` (строка 238)

#### 1.2. GET `/companies/{company_id}/snapshots`

```222:235:backend/app/api/v2/endpoints/analytics.py
async def get_company_snapshots(...):
    # Получение списка snapshots
    snapshots = await analytics.get_snapshots(company_id, period, limit)
    
    # Конвертация каждого snapshot в response
    snapshot_models = [_snapshot_to_response(snapshot) for snapshot in snapshots]
    
    return SnapshotSeriesResponse(...)
```

**Где формируется:**
- Список snapshots - получается через `analytics.get_snapshots()` (строка 229)
- Response - формируется через `_snapshot_to_response()` для каждого snapshot (строка 230)

#### 1.3. GET `/graph`

```360:369:backend/app/api/v2/endpoints/analytics.py
async def get_graph_edges(...):
    # SQL запрос для получения графовых ребер
    stmt = select(AnalyticsGraphEdge)...
    
    # Конвертация в response
    return [_edge_to_response(edge) for edge in edges]
```

**Где формируется:**
- Графовые ребра - получаются из БД через SQL запрос (строки 360-367)
- Response - формируется через `_edge_to_response()` (строка 369)

---

### 2. **Сервис вычисления snapshot** - основная логика

**Файл:** `backend/app/domains/analytics/services/snapshot_service.py`

#### 2.1. `compute_snapshot_for_period()` - главный метод

```139:190:backend/app/domains/analytics/services/snapshot_service.py
async def compute_snapshot_for_period(...):
    # 1. Агрегация новостей
    news_stats = await self._aggregate_news(company_id, period_start, period_end)
    
    # 2. Загрузка событий
    changes = await self._load_change_events(company_id, period_start, period_end)
    
    # 3. Подсчет изменений
    pricing_changes, feature_updates = self._summarise_change_events(changes)
    funding_events = news_stats.get("funding_events", 0)
    
    # 4. Вычисление velocity
    innovation_velocity = self._calculate_velocity(period_enum, pricing_changes, feature_updates)
    
    # 5. Построение компонентов
    components = self._build_components(
        news_stats, pricing_changes, feature_updates,
        funding_events, innovation_velocity
    )
    
    # 6. Вычисление impact_score
    impact_score = sum(component["score"] for component in components)
    
    # 7. Вычисление trend_delta
    previous_snapshot = await self._get_previous_snapshot(...)
    trend_delta = self._compute_trend_delta(previous_snapshot, impact_score)
    
    # 8. Создание/обновление snapshot в БД
    snapshot = await self._upsert_snapshot(...)
    
    # 9. Сохранение компонентов
    await self._persist_components(snapshot, components)
    
    return snapshot
```

**Где формируется:**
- **news_stats** - метод `_aggregate_news()` (строка 151) → SQL агрегация новостей
- **changes** - метод `_load_change_events()` (строка 152) → SQL запрос событий
- **pricing_changes, feature_updates** - метод `_summarise_change_events()` (строка 154)
- **innovation_velocity** - метод `_calculate_velocity()` (строка 157)
- **components** - метод `_build_components()` (строка 158) → построение компонентов impact
- **impact_score** - сумма всех компонентов (строка 165)
- **trend_delta** - метод `_compute_trend_delta()` (строка 168)
- **snapshot** - метод `_upsert_snapshot()` (строка 170) → создание/обновление в БД

#### 2.2. `_aggregate_news()` - агрегация новостей

```251:314:backend/app/domains/analytics/services/snapshot_service.py
async def _aggregate_news(...):
    # SQL запрос с агрегацией
    stmt = select(
        func.count(NewsItem.id).label("total"),
        func.sum(case(...)).label("positive"),
        func.sum(case(...)).label("negative"),
        func.sum(case(...)).label("neutral"),
        func.coalesce(func.avg(NewsItem.priority_score), 0.0).label("avg_priority"),
        func.sum(case(...)).label("funding_events"),
    ).where(
        NewsItem.company_id == company_id,
        NewsItem.published_at >= start_utc,
        NewsItem.published_at < end_utc,
    )
    
    # Вычисление average_sentiment
    average_sentiment = (positive - negative) / float(total_news)
    
    return {
        "total_news": ...,
        "positive_news": ...,
        "negative_news": ...,
        "neutral_news": ...,
        "average_priority": ...,
        "average_sentiment": ...,
        "funding_events": ...,
    }
```

**Где формируется:**
- SQL запрос с агрегацией (строки 260-294)
- Вычисление sentiment (строки 302-304)
- Словарь со статистикой (строки 306-314)

#### 2.3. `_build_components()` - построение компонентов impact

```377:427:backend/app/domains/analytics/services/snapshot_service.py
def _build_components(...):
    # Вычисление news_signal
    positive_delta = news_stats["positive_news"] - news_stats["negative_news"]
    news_signal = (
        news_stats["total_news"] * self.IMPACT_WEIGHTS["news_volume"]
        + positive_delta * self.IMPACT_WEIGHTS["sentiment_delta"]
        + news_stats["average_priority"] * self.IMPACT_WEIGHTS["priority"]
    )
    
    # Создание компонентов
    components = [
        {
            "component_type": ImpactComponentType.NEWS_SIGNAL,
            "weight": self.IMPACT_WEIGHTS["news_volume"],
            "score": news_signal,
            "metadata": {...},
        },
        {
            "component_type": ImpactComponentType.PRICING_CHANGE,
            "weight": self.IMPACT_WEIGHTS["pricing_change"],
            "score": pricing_changes * self.IMPACT_WEIGHTS["pricing_change"],
            "metadata": {...},
        },
        # ... другие компоненты
    ]
    
    return components
```

**Где формируется:**
- **news_signal** - вычисляется на основе новостей (строки 385-390)
- **components** - список компонентов с весами и метаданными (строки 392-427)
- **Веса** - определены в `IMPACT_WEIGHTS` (строки 42-50)

#### 2.4. `_upsert_snapshot()` - создание/обновление snapshot

```430:508:backend/app/domains/analytics/services/snapshot_service.py
async def _upsert_snapshot(...):
    # Поиск существующего snapshot
    snapshot = result.scalar_one_or_none()
    
    if snapshot is None:
        # Создание нового snapshot
        snapshot = CompanyAnalyticsSnapshot(
            company_id=company_id,
            period=period_db_value,
            period_start=period_start,
            period_end=period_end,
            news_total=news_stats["total_news"],
            news_positive=news_stats["positive_news"],
            # ... остальные поля
            impact_score=impact_score,
            innovation_velocity=innovation_velocity,
            trend_delta=trend_delta,
            metric_breakdown=metrics_breakdown,
        )
        self.db.add(snapshot)
    else:
        # Обновление существующего snapshot
        snapshot.news_total = news_stats["total_news"]
        # ... обновление остальных полей
    
    return snapshot
```

**Где формируется:**
- Новый snapshot - создается объект `CompanyAnalyticsSnapshot` (строки 468-486)
- Обновление snapshot - обновляются поля существующего (строки 491-506)
- **metric_breakdown** - словарь с метриками (строки 458-463)

---

### 3. **Конвертация в Response** - форматирование для API

**Файл:** `backend/app/api/v2/endpoints/analytics.py`

#### 3.1. `_snapshot_to_response()` - конвертация snapshot

```475:509:backend/app/api/v2/endpoints/analytics.py
def _snapshot_to_response(snapshot) -> CompanyAnalyticsSnapshotResponse:
    return CompanyAnalyticsSnapshotResponse(
        id=snapshot_id,
        company_id=snapshot.company_id,
        period=snapshot.period,
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        news_total=snapshot.news_total,
        news_positive=snapshot.news_positive,
        # ... остальные поля
        components=[
            ImpactComponentResponse(
                id=getattr(component, 'id', None),
                component_type=component.component_type,
                weight=component.weight,
                score_contribution=component.score_contribution,
                metadata=getattr(component, 'metadata_json', None) or {},
            )
            for component in components_list
        ],
    )
```

**Где формируется:**
- Response объект - создается `CompanyAnalyticsSnapshotResponse` (строки 480-508)
- Components - конвертируются из `ImpactComponent` в `ImpactComponentResponse` (строки 499-507)

---

## 📋 Сводная таблица мест формирования данных

| Данные | Где формируется | Файл | Метод/Строки |
|--------|----------------|------|--------------|
| **period_start** | Эндпоинт | `analytics.py` | `get_latest_snapshot()` (133-136) |
| **news_stats** | Сервис | `snapshot_service.py` | `_aggregate_news()` (251-314) |
| **changes** | Сервис | `snapshot_service.py` | `_load_change_events()` (316-341) |
| **pricing_changes, feature_updates** | Сервис | `snapshot_service.py` | `_summarise_change_events()` (343-365) |
| **innovation_velocity** | Сервис | `snapshot_service.py` | `_calculate_velocity()` (367-375) |
| **components** | Сервис | `snapshot_service.py` | `_build_components()` (377-427) |
| **impact_score** | Сервис | `snapshot_service.py` | `compute_snapshot_for_period()` (165) |
| **trend_delta** | Сервис | `snapshot_service.py` | `_compute_trend_delta()` (549-557) |
| **snapshot (БД)** | Сервис | `snapshot_service.py` | `_upsert_snapshot()` (430-508) |
| **empty snapshot** | Эндпоинт | `analytics.py` | `get_latest_snapshot()` (187-204) |
| **response** | Эндпоинт | `analytics.py` | `_snapshot_to_response()` (475-509) |

---

## 🔄 Поток данных

```
1. API Request → GET /companies/{id}/impact/latest
   ↓
2. Эндпоинт: get_latest_snapshot()
   ├─ Проверка существующего snapshot
   ├─ Если нет → compute_snapshot_for_period()
   └─ Если ошибка → создание пустого snapshot
   ↓
3. Сервис: compute_snapshot_for_period()
   ├─ _aggregate_news() → SQL агрегация новостей
   ├─ _load_change_events() → SQL загрузка событий
   ├─ _summarise_change_events() → подсчет изменений
   ├─ _calculate_velocity() → вычисление velocity
   ├─ _build_components() → построение компонентов
   ├─ impact_score = sum(components)
   ├─ _compute_trend_delta() → вычисление тренда
   ├─ _upsert_snapshot() → создание/обновление в БД
   └─ _persist_components() → сохранение компонентов
   ↓
4. Эндпоинт: _snapshot_to_response()
   └─ Конвертация в CompanyAnalyticsSnapshotResponse
   ↓
5. API Response → JSON с данными snapshot
```

---

## 📝 Важные константы

**Веса компонентов:**
```42:50:backend/app/domains/analytics/services/snapshot_service.py
IMPACT_WEIGHTS: Dict[str, float] = {
    "news_volume": 0.25,
    "sentiment_delta": 0.15,
    "priority": 0.10,
    "pricing_change": 0.20,
    "feature_update": 0.15,
    "funding_event": 0.10,
    "velocity": 0.05,
}
```

**Периоды:**
```52:56:backend/app/domains/analytics/services/snapshot_service.py
PERIOD_LOOKUPS: Dict[AnalyticsPeriod, timedelta] = {
    AnalyticsPeriod.DAILY: timedelta(days=1),
    AnalyticsPeriod.WEEKLY: timedelta(days=7),
    AnalyticsPeriod.MONTHLY: timedelta(days=30),
}
```




