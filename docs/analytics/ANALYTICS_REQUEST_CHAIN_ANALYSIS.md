# Полный анализ цепочки запроса: GET /api/v2/analytics/companies/{id}/impact/latest

## 🔍 Обзор проблемы

**Запрос:** `GET http://localhost:8000/api/v2/analytics/companies/75eee989-a419-4220-bdc6-810c4854a1fe/impact/latest?period=daily`

**Ошибка:** `404 (Not Found)`

## 📊 Полная цепочка запроса (от фронтенда до БД)

### 1. **Фронтенд: React Component** 
📍 `CompetitorAnalysisPage.tsx:164`

```typescript
// Триггер запроса через React Query
usePrefetchAnalytics.ts:26
```

### 2. **Фронтенд: React Query Hook**
📍 `usePrefetchAnalytics.ts:28`

```typescript
queryFn @ usePrefetchAnalytics.ts:28
```

### 3. **Фронтенд: Custom Hook**
📍 `useCompanyAnalyticsInsights.ts:29`

```typescript
fetchCompanyAnalyticsInsights(companyId: string)
  └─> Promise.allSettled([
        ApiService.getLatestAnalyticsSnapshot(companyId),  // ← Наш запрос
        ApiService.getAnalyticsSnapshots(companyId, 'daily', 60),
        ApiService.getAnalyticsGraph(companyId, undefined, 25)
      ])
```

**Обработка ошибок:**
- Если `status === 404` → показывается сообщение: "Аналитика ещё не построена. Запустите пересчёт, чтобы получить метрики."
- Иначе → логируется ошибка в консоль

### 4. **Фронтенд: API Service**
📍 `frontend/src/services/api.ts:656`

```typescript
static async getLatestAnalyticsSnapshot(
  companyId: string,
  period: AnalyticsPeriod = 'daily'
): Promise<CompanyAnalyticsSnapshot> {
  const response = await apiV2.get<CompanyAnalyticsSnapshot>(
    `/analytics/companies/${companyId}/impact/latest`, 
    { params: { period } }
  )
  return response.data
}
```

**Конфигурация axios:**
```typescript
// frontend/src/services/api.ts:225-231
export const apiV2 = axios.create({
  baseURL: API_V2_BASE,  // '/api/v2' или '${API_BASE_URL}/api/v2'
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})
```

**Итоговый URL:** `http://localhost:8000/api/v2/analytics/companies/{companyId}/impact/latest?period=daily`

### 5. **Backend: FastAPI Router Registration**
📍 `backend/main.py:132-133`

```python
if settings.ENABLE_ANALYTICS_V2:
    app.include_router(api_v2_router)
```

**Проверка:** `ENABLE_ANALYTICS_V2` должен быть `True` (по умолчанию `True`)

### 6. **Backend: API v2 Router**
📍 `backend/app/api/v2/api.py:9-18`

```python
api_v2_router = APIRouter(
    prefix="/api/v2",
    tags=["API v2"],
)

api_v2_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"],
)
```

**Итоговый префикс:** `/api/v2/analytics`

### 7. **Backend: Analytics Router**
📍 `backend/app/api/v2/endpoints/analytics.py:54`

```python
router = APIRouter()
```

### 8. **Backend: Endpoint Handler**
📍 `backend/app/api/v2/endpoints/analytics.py:84-201`

```python
@router.get(
    "/companies/{company_id}/impact/latest",
    response_model=CompanyAnalyticsSnapshotResponse,
    summary="Get latest analytics snapshot",
)
async def get_latest_snapshot(
    company_id: UUID,
    period: str = Query(default="daily", description="Analytics period: daily, weekly, or monthly"),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsFacade = Depends(get_analytics_facade),
) -> CompanyAnalyticsSnapshotResponse:
```

**Полный путь:** `/api/v2` + `/analytics` + `/companies/{company_id}/impact/latest` = `/api/v2/analytics/companies/{company_id}/impact/latest` ✅

### 9. **Backend: Dependencies**

#### 9.1. Authentication
📍 `backend/app/api/dependencies.py:23-74`

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # Проверка токена и получение пользователя из БД
```

**Если токен невалиден → 401 Unauthorized**

#### 9.2. Analytics Facade
📍 `backend/app/api/dependencies.py:161-167`

```python
def get_analytics_facade(
    db: AsyncSession = Depends(get_db),
) -> AnalyticsFacade:
    return AnalyticsFacade(db)
```

**Создает:** `AnalyticsFacade` с сессией БД

### 10. **Backend: Domain Layer - AnalyticsFacade**
📍 `backend/app/domains/analytics/facade.py:46-51`

```python
async def get_latest_snapshot(
    self,
    company_id: UUID,
    period: AnalyticsPeriod,
) -> Optional[CompanyAnalyticsSnapshot]:
    return await self.snapshots.get_latest_snapshot(company_id, period)
```

**Делегирует:** `SnapshotService.get_latest_snapshot()`

### 11. **Backend: Domain Layer - SnapshotService**
📍 `backend/app/domains/analytics/services/snapshot_service.py:106-122`

```python
async def get_latest_snapshot(
    self,
    company_id: UUID,
    period: AnalyticsPeriod | str = AnalyticsPeriod.DAILY,
) -> Optional[CompanyAnalyticsSnapshot]:
    stmt = (
        select(CompanyAnalyticsSnapshot)
        .where(
            CompanyAnalyticsSnapshot.company_id == company_id,
            self._period_filter(CompanyAnalyticsSnapshot.period, period),
        )
        .order_by(CompanyAnalyticsSnapshot.period_start.desc())
        .options(selectinload(CompanyAnalyticsSnapshot.components))
        .limit(1)
    )
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()
```

**SQL Query (примерно):**
```sql
SELECT 
    company_analytics_snapshots.*,
    impact_components.*
FROM company_analytics_snapshots
LEFT JOIN impact_components ON impact_components.snapshot_id = company_analytics_snapshots.id
WHERE 
    company_analytics_snapshots.company_id = :company_id
    AND company_analytics_snapshots.period = :period
ORDER BY company_analytics_snapshots.period_start DESC
LIMIT 1
```

### 12. **Backend: Database Model**
📍 `backend/app/models/analytics.py:106-159`

```python
class CompanyAnalyticsSnapshot(BaseModel):
    __tablename__ = "company_analytics_snapshots"
    
    company_id = Column(PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period = Column(analytics_period_enum.copy(), nullable=False, default=AnalyticsPeriod.DAILY)
    
    # ... метрики ...
    
    components = relationship("ImpactComponent", back_populates="snapshot", lazy="selectin")
    
    __table_args__ = (
        UniqueConstraint("company_id", "period_start", "period", name="uq_company_snapshot_period"),
        Index("ix_company_snapshot_company_period", "company_id", "period", "period_start"),
    )
```

**Таблица БД:** `company_analytics_snapshots`

### 13. **Backend: Response Transformation**
📍 `backend/app/api/v2/endpoints/analytics.py:456-490`

```python
def _snapshot_to_response(snapshot) -> CompanyAnalyticsSnapshotResponse:
    return CompanyAnalyticsSnapshotResponse(
        id=snapshot_id,
        company_id=snapshot.company_id,
        period=snapshot.period,
        # ... все поля ...
        components=[...]
    )
```

## 🔴 Возможные причины 404

### 1. **Маршрут не найден (FastAPI)**
- ❌ Роутер не зарегистрирован (`ENABLE_ANALYTICS_V2 = False`)
- ❌ Неправильный порядок маршрутов (более общий маршрут перехватывает запрос)
- ❌ Конфликт с другими маршрутами

**Проверка:**
```bash
# Проверить, что роутер зарегистрирован
grep -r "ENABLE_ANALYTICS_V2" backend/app/core/config.py

# Проверить доступные маршруты
curl http://localhost:8000/docs
```

### 2. **Аутентификация не прошла**
- ❌ Токен отсутствует или невалиден
- ❌ Пользователь не найден в БД

**Проверка:** Должна быть ошибка 401, а не 404

### 3. **Данные не найдены в БД**
- ❌ Snapshot не существует для данной компании и периода
- ❌ Компания не существует

**Логика обработки:**
```python
# backend/app/api/v2/endpoints/analytics.py:111-199
snapshot = await analytics.get_latest_snapshot(company_id, period_enum)
if not snapshot:
    # Пытается автоматически создать snapshot
    # Если не удается → возвращает 404
```

### 4. **Ошибка при создании snapshot**
- ❌ Ошибка в `compute_snapshot_for_period()`
- ❌ Ошибка при сохранении пустого snapshot в БД
- ❌ Проблемы с транзакцией БД

**Код:**
```python
# backend/app/api/v2/endpoints/analytics.py:188-199
except Exception as db_exc:
    logger.error("Failed to create empty snapshot...")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Snapshot not found and could not be created automatically",
    ) from db_exc
```

## ✅ Диагностика

### Шаг 1: Проверить регистрацию роутера
```bash
# Проверить логи сервера при старте
# Должно быть: "Starting AI Competitor Insight Hub API..."

# Проверить настройки
grep ENABLE_ANALYTICS_V2 backend/app/core/config.py
```

### Шаг 2: Проверить доступность эндпоинта
```bash
# Через Swagger UI
open http://localhost:8000/docs

# Или через curl (с токеном)
curl -X GET "http://localhost:8000/api/v2/analytics/companies/75eee989-a419-4220-bdc6-810c4854a1fe/impact/latest?period=daily" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Шаг 3: Проверить логи сервера
```python
# Должны быть логи:
logger.info("get_latest_snapshot called: company_id=%s, period=%s, user_id=%s", ...)
logger.debug("get_latest_snapshot result: snapshot=%s", ...)
```

### Шаг 4: Проверить данные в БД
```sql
-- Проверить существование компании
SELECT id, name FROM companies WHERE id = '75eee989-a419-4220-bdc6-810c4854a1fe';

-- Проверить существование snapshots
SELECT id, company_id, period, period_start, period_end 
FROM company_analytics_snapshots 
WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe' 
  AND period = 'daily'
ORDER BY period_start DESC 
LIMIT 5;
```

### Шаг 5: Проверить порядок маршрутов
```python
# backend/app/api/v2/endpoints/analytics.py
# Важно: более специфичные маршруты должны быть ПЕРЕД общими

@router.get("/companies/{company_id}/impact/latest")  # ← Должен быть ПЕРВЫМ
@router.get("/companies/{company_id}/snapshots")     # ← Должен быть ПОСЛЕ
```

## 🔧 Решения

### Решение 1: Перезапустить сервер
```bash
# После изменений в коде обязательно перезапустить
cd backend
uvicorn app.main:app --reload
```

### Решение 2: Проверить порядок маршрутов
Убедиться, что `/impact/latest` идет ПЕРЕД `/snapshots` в файле `analytics.py`

### Решение 3: Проверить данные в БД
Если snapshot не существует, эндпоинт пытается создать его автоматически. Если это не удается, проверьте:
- Существует ли компания в БД
- Есть ли права на создание записей
- Нет ли ошибок в логах при создании snapshot

### Решение 4: Добавить больше логирования
```python
# В начале функции get_latest_snapshot
logger.info("=== get_latest_snapshot START ===")
logger.info(f"company_id={company_id}, period={period}, user_id={current_user.id}")
```

## 📝 Файлы в цепочке

1. **Фронтенд:**
   - `frontend/src/pages/CompetitorAnalysisPage.tsx` - триггер
   - `frontend/src/features/competitor-analysis/hooks/usePrefetchAnalytics.ts` - React Query
   - `frontend/src/features/competitor-analysis/hooks/useCompanyAnalyticsInsights.ts` - хук
   - `frontend/src/services/api.ts` - API клиент

2. **Backend:**
   - `backend/main.py` - регистрация роутера
   - `backend/app/api/v2/api.py` - конфигурация API v2
   - `backend/app/api/v2/endpoints/analytics.py` - эндпоинт
   - `backend/app/api/dependencies.py` - зависимости (auth, facade)
   - `backend/app/domains/analytics/facade.py` - фасад
   - `backend/app/domains/analytics/services/snapshot_service.py` - сервис
   - `backend/app/models/analytics.py` - модель БД

3. **База данных:**
   - Таблица: `company_analytics_snapshots`
   - Таблица: `impact_components`
   - Таблица: `companies`

## 🎯 Рекомендации

1. **Всегда проверяйте логи сервера** при получении 404
2. **Убедитесь, что сервер перезапущен** после изменений в коде
3. **Проверяйте порядок маршрутов** в FastAPI (специфичные → общие)
4. **Используйте Swagger UI** (`/docs`) для проверки доступности эндпоинтов
5. **Проверяйте данные в БД** перед отладкой кода




