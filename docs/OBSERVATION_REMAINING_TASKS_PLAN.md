# План реализации недостающих компонентов системы наблюдения

**Дата создания:** 2025-01-27  
**Статус:** Требуется реализация  
**Приоритет:** Высокий (критичные компоненты)

---

## 📊 Обзор

План реализации 4 критических компонентов:
1. ✅ API endpoint `/monitoring/changes` - **КРИТИЧНО**
2. ✅ Настройки мониторинга в SettingsPage
3. ✅ Unit и интеграционные тесты
4. ✅ API документация (Swagger)

**Общая оценка времени:** 8-12 рабочих дней

---

## 1️⃣ API Endpoint `/monitoring/changes` - КРИТИЧНО

**Приоритет:** 🔴 **ВЫСОКИЙ**  
**Оценка времени:** 1-2 дня  
**Блокирует:** `MonitoringChangesTable` компонент

### Задачи

#### 1.1. Backend: Создать endpoint (1 день)

**Файл:** `backend/app/api/v1/endpoints/companies.py`

**Задача 1.1.1**: Добавить endpoint `GET /api/v1/companies/monitoring/changes`

```python
@router.get("/monitoring/changes")
async def get_monitoring_changes(
    company_ids: Optional[str] = Query(None, description="Comma-separated company UUIDs"),
    change_types: Optional[str] = Query(None, description="Comma-separated change types"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=500, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get monitoring change events for companies.
    
    Query parameters:
    - company_ids: Comma-separated list of company UUIDs (optional)
    - change_types: Comma-separated list of change types (optional)
      Valid types: website_structure, marketing_banner, marketing_landing, 
                   marketing_product, marketing_jobs, seo_meta, seo_structure, pricing
    - date_from: Filter events from this date (ISO format)
    - date_to: Filter events to this date (ISO format)
    - limit: Maximum number of results (1-500, default: 50)
    - offset: Offset for pagination (default: 0)
    
    Returns:
    - events: List of change events
    - total: Total count of matching events
    - has_more: Whether there are more results
    """
```

**Детали реализации:**

1. **Парсинг параметров:**
   ```python
   # Parse company_ids
   company_id_list = []
   if company_ids:
       company_id_list = [uuid.UUID(cid.strip()) for cid in company_ids.split(',') if cid.strip()]
   
   # Parse change_types
   change_type_list = []
   if change_types:
       change_type_list = [ct.strip() for ct in change_types.split(',') if ct.strip()]
   ```

2. **Построение запроса:**
   ```python
   from sqlalchemy import and_, or_
   from app.models.competitor import CompetitorChangeEvent
   from app.models.company import Company
   from app.core.access_control import check_company_access
   
   # Build base query
   query = select(CompetitorChangeEvent).join(Company)
   
   # Access control filter
   if current_user:
       company_filter = Company.user_id == current_user.id
   else:
       company_filter = Company.user_id.is_(None)
   
   conditions = [company_filter]
   
   # Company filter
   if company_id_list:
       # Check access for each company
       accessible_ids = []
       for cid in company_id_list:
           if await check_company_access(str(cid), current_user, db):
               accessible_ids.append(cid)
       if accessible_ids:
           conditions.append(CompetitorChangeEvent.company_id.in_(accessible_ids))
       else:
           return {"events": [], "total": 0, "has_more": False}
   
   # Change type filter (from raw_diff.type or source_type)
   if change_type_list:
       # Map monitoring change types to source_type or check raw_diff
       type_conditions = []
       for ct in change_type_list:
           # Check if type is in raw_diff or can be inferred from source_type
           # This requires checking raw_diff JSON field
           type_conditions.append(
               CompetitorChangeEvent.raw_diff['type'].astext == ct
           )
       if type_conditions:
           conditions.append(or_(*type_conditions))
   
   # Date filters
   if date_from:
       conditions.append(CompetitorChangeEvent.detected_at >= date_from)
   if date_to:
       conditions.append(CompetitorChangeEvent.detected_at <= date_to)
   
   # Apply all conditions
   if conditions:
       query = query.where(and_(*conditions))
   
   # Order by detected_at descending
   query = query.order_by(CompetitorChangeEvent.detected_at.desc())
   ```

3. **Пагинация и подсчет:**
   ```python
   # Get total count
   count_query = select(func.count()).select_from(
       select(CompetitorChangeEvent.id).join(Company).where(and_(*conditions)).subquery()
   )
   total_result = await db.execute(count_query)
   total = total_result.scalar() or 0
   
   # Apply limit and offset
   query = query.limit(limit).offset(offset)
   
   # Execute query
   result = await db.execute(query)
   events = result.scalars().all()
   ```

4. **Трансформация данных:**
   ```python
   # Map to response format
   events_data = []
   for event in events:
       # Extract change_type from raw_diff.type or infer from source_type
       change_type = event.raw_diff.get('type', 'other')
       
       # Map to MonitoringChangeEvent format
       events_data.append({
           "id": str(event.id),
           "company_id": str(event.company_id),
           "change_type": change_type,
           "change_summary": event.change_summary,
           "detected_at": event.detected_at.isoformat(),
           "source_url": event.raw_diff.get('source_url'),
           "details": event.raw_diff
       })
   
   return {
       "events": events_data,
       "total": total,
       "has_more": (offset + limit) < total
   }
   ```

**Файлы для изменения:**
- `backend/app/api/v1/endpoints/companies.py` - добавить endpoint после `get_monitoring_stats`

**Зависимости:**
- Модель `CompetitorChangeEvent` уже существует ✅
- Типы данных уже определены ✅
- Frontend метод `getMonitoringChanges()` уже существует ✅

---

#### 1.2. Backend: Добавить схемы Pydantic (опционально, 0.5 дня)

**Файл:** `backend/app/schemas/monitoring.py` (новый файл)

**Создать схемы:**
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class MonitoringChangeEventSchema(BaseModel):
    id: str
    company_id: str
    change_type: str
    change_summary: str
    detected_at: datetime
    source_url: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

class MonitoringChangesResponseSchema(BaseModel):
    events: List[MonitoringChangeEventSchema]
    total: int
    has_more: bool

class MonitoringChangesFiltersSchema(BaseModel):
    company_ids: Optional[List[str]] = None
    change_types: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)
```

---

#### 1.3. Тестирование endpoint (0.5 дня)

**Файл:** `backend/tests/integration/api/test_monitoring_changes_endpoint.py` (новый)

**Тесты:**
- ✅ Получение изменений без фильтров
- ✅ Фильтрация по company_ids
- ✅ Фильтрация по change_types
- ✅ Фильтрация по датам
- ✅ Пагинация
- ✅ Проверка доступа (только свои компании)

---

## 2️⃣ Настройки мониторинга в SettingsPage

**Приоритет:** 🟡 **СРЕДНИЙ**  
**Оценка времени:** 2-3 дня

### Задачи

#### 2.1. Backend: Расширить UserPreferences модель (0.5 дня)

**Файл:** `backend/app/models/preferences.py`

**Задача 2.1.1**: Добавить поля для настроек мониторинга

```python
# Добавить в модель UserPreferences после telegram_enabled

# Monitoring settings
monitoring_enabled = Column(Boolean, default=True)
monitoring_check_frequency = Column(
    SQLEnum('hourly', '6h', 'daily', 'weekly', name='monitoring_frequency'),
    default='daily'
)
monitoring_notify_on_changes = Column(Boolean, default=True)
monitoring_change_types = Column(
    JSON, 
    default=lambda: [
        'website_structure',
        'marketing_banner',
        'marketing_landing',
        'marketing_product',
        'marketing_jobs',
        'seo_meta',
        'seo_structure',
        'pricing'
    ]
)
monitoring_auto_refresh = Column(Boolean, default=True)
monitoring_notification_channels = Column(
    JSON,
    default=lambda: {'email': True, 'telegram': False}
)
```

**Задача 2.1.2**: Создать миграцию

**Файл:** `backend/alembic/versions/XXX_add_monitoring_preferences.py`

```python
"""add_monitoring_preferences

Revision ID: XXX
Revises: <last_revision>
Create Date: 2025-01-27
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # Add monitoring_enabled
    op.add_column('user_preferences', 
        sa.Column('monitoring_enabled', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # Create monitoring_frequency enum
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'monitoring_frequency') THEN
                CREATE TYPE monitoring_frequency AS ENUM ('hourly', '6h', 'daily', 'weekly');
            END IF;
        END $$;
    """)
    
    # Add monitoring_check_frequency
    op.add_column('user_preferences',
        sa.Column('monitoring_check_frequency', 
                 sa.Enum('hourly', '6h', 'daily', 'weekly', name='monitoring_frequency'),
                 nullable=False,
                 server_default='daily')
    )
    
    # Add other monitoring fields
    op.add_column('user_preferences',
        sa.Column('monitoring_notify_on_changes', sa.Boolean(), nullable=False, server_default='true')
    )
    op.add_column('user_preferences',
        sa.Column('monitoring_change_types', sa.JSON(), nullable=True)
    )
    op.add_column('user_preferences',
        sa.Column('monitoring_auto_refresh', sa.Boolean(), nullable=False, server_default='true')
    )
    op.add_column('user_preferences',
        sa.Column('monitoring_notification_channels', sa.JSON(), nullable=True)
    )
    
    # Set default values for JSON columns
    op.execute("""
        UPDATE user_preferences 
        SET monitoring_change_types = '[
            "website_structure",
            "marketing_banner",
            "marketing_landing",
            "marketing_product",
            "marketing_jobs",
            "seo_meta",
            "seo_structure",
            "pricing"
        ]'::jsonb
        WHERE monitoring_change_types IS NULL;
    """)
    
    op.execute("""
        UPDATE user_preferences 
        SET monitoring_notification_channels = '{"email": true, "telegram": false}'::jsonb
        WHERE monitoring_notification_channels IS NULL;
    """)

def downgrade() -> None:
    op.drop_column('user_preferences', 'monitoring_notification_channels')
    op.drop_column('user_preferences', 'monitoring_auto_refresh')
    op.drop_column('user_preferences', 'monitoring_change_types')
    op.drop_column('user_preferences', 'monitoring_notify_on_changes')
    op.drop_column('user_preferences', 'monitoring_check_frequency')
    op.drop_column('user_preferences', 'monitoring_enabled')
    op.execute("DROP TYPE IF EXISTS monitoring_frequency;")
```

---

#### 2.2. Backend: API endpoints для настроек (1 день)

**Файл:** `backend/app/api/v1/endpoints/users.py`

**Задача 2.2.1**: Добавить endpoint `GET /api/v1/users/monitoring/preferences`

```python
@router.get("/monitoring/preferences")
async def get_monitoring_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user monitoring preferences.
    """
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    preferences = result.scalar_one_or_none()
    
    if not preferences:
        # Create default preferences
        preferences = await create_default_preferences(current_user.id, db)
    
    return {
        "monitoring_enabled": preferences.monitoring_enabled,
        "monitoring_check_frequency": safe_enum_to_string(
            preferences.monitoring_check_frequency, "daily"
        ),
        "monitoring_notify_on_changes": preferences.monitoring_notify_on_changes,
        "monitoring_change_types": preferences.monitoring_change_types or [],
        "monitoring_auto_refresh": preferences.monitoring_auto_refresh,
        "monitoring_notification_channels": (
            preferences.monitoring_notification_channels or 
            {"email": True, "telegram": False}
        )
    }
```

**Задача 2.2.2**: Добавить endpoint `PUT /api/v1/users/monitoring/preferences`

```python
@router.put("/monitoring/preferences")
async def update_monitoring_preferences(
    monitoring_enabled: Optional[bool] = Body(None),
    monitoring_check_frequency: Optional[str] = Body(None),
    monitoring_notify_on_changes: Optional[bool] = Body(None),
    monitoring_change_types: Optional[List[str]] = Body(None),
    monitoring_auto_refresh: Optional[bool] = Body(None),
    monitoring_notification_channels: Optional[Dict[str, bool]] = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user monitoring preferences.
    """
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    preferences = result.scalar_one_or_none()
    
    if not preferences:
        preferences = await create_default_preferences(current_user.id, db)
    
    # Update fields
    if monitoring_enabled is not None:
        preferences.monitoring_enabled = monitoring_enabled
    if monitoring_check_frequency is not None:
        preferences.monitoring_check_frequency = monitoring_check_frequency
    if monitoring_notify_on_changes is not None:
        preferences.monitoring_notify_on_changes = monitoring_notify_on_changes
    if monitoring_change_types is not None:
        preferences.monitoring_change_types = monitoring_change_types
    if monitoring_auto_refresh is not None:
        preferences.monitoring_auto_refresh = monitoring_auto_refresh
    if monitoring_notification_channels is not None:
        preferences.monitoring_notification_channels = monitoring_notification_channels
    
    await db.commit()
    await db.refresh(preferences)
    
    return {
        "monitoring_enabled": preferences.monitoring_enabled,
        "monitoring_check_frequency": safe_enum_to_string(
            preferences.monitoring_check_frequency, "daily"
        ),
        "monitoring_notify_on_changes": preferences.monitoring_notify_on_changes,
        "monitoring_change_types": preferences.monitoring_change_types or [],
        "monitoring_auto_refresh": preferences.monitoring_auto_refresh,
        "monitoring_notification_channels": (
            preferences.monitoring_notification_channels or 
            {"email": True, "telegram": False}
        )
    }
```

---

#### 2.3. Frontend: Добавить API методы (0.5 дня)

**Файл:** `frontend/src/services/api.ts`

**Задача 2.3.1**: Добавить методы для настроек мониторинга

```typescript
/**
 * Get monitoring preferences
 */
static async getMonitoringPreferences(): Promise<{
  monitoring_enabled: boolean
  monitoring_check_frequency: 'hourly' | '6h' | 'daily' | 'weekly'
  monitoring_notify_on_changes: boolean
  monitoring_change_types: string[]
  monitoring_auto_refresh: boolean
  monitoring_notification_channels: { email: boolean; telegram: boolean }
}> {
  const response = await api.get('/users/monitoring/preferences')
  return response.data
}

/**
 * Update monitoring preferences
 */
static async updateMonitoringPreferences(preferences: {
  monitoring_enabled?: boolean
  monitoring_check_frequency?: 'hourly' | '6h' | 'daily' | 'weekly'
  monitoring_notify_on_changes?: boolean
  monitoring_change_types?: string[]
  monitoring_auto_refresh?: boolean
  monitoring_notification_channels?: { email: boolean; telegram: boolean }
}): Promise<void> {
  await api.put('/users/monitoring/preferences', preferences)
}
```

**Задача 2.3.2**: Обновить типы

**Файл:** `frontend/src/types/index.ts`

```typescript
export interface MonitoringPreferences {
  monitoring_enabled: boolean
  monitoring_check_frequency: 'hourly' | '6h' | 'daily' | 'weekly'
  monitoring_notify_on_changes: boolean
  monitoring_change_types: string[]
  monitoring_auto_refresh: boolean
  monitoring_notification_channels: {
    email: boolean
    telegram: boolean
  }
}
```

---

#### 2.4. Frontend: Создать компонент настроек (1 день)

**Файл:** `frontend/src/components/settings/MonitoringSettings.tsx` (новый)

**Структура компонента:**

```typescript
export default function MonitoringSettings() {
  const { data: preferences, isLoading } = useQuery({
    queryKey: ['monitoring-preferences'],
    queryFn: ApiService.getMonitoringPreferences,
  })
  
  const updateMutation = useMutation({
    mutationFn: ApiService.updateMonitoringPreferences,
    onSuccess: () => {
      queryClient.invalidateQueries(['monitoring-preferences'])
      toast.success('Настройки сохранены')
    }
  })
  
  // Форма с полями:
  // - Включить/выключить мониторинг (чекбокс)
  // - Частота проверки (селект: hourly, 6h, daily, weekly)
  // - Уведомления о изменениях (чекбокс)
  // - Типы изменений для уведомлений (мультиселект чекбоксов)
  // - Автоматическое обновление (чекбокс)
  // - Каналы уведомлений (чекбоксы: Email, Telegram)
  
  return (
    <div className="space-y-6">
      {/* Форма настроек */}
    </div>
  )
}
```

---

#### 2.5. Frontend: Интегрировать в SettingsPage (0.5 дня)

**Файл:** `frontend/src/pages/SettingsPage.tsx`

**Задача 2.5.1**: Добавить секцию "Monitoring Settings"

```typescript
import MonitoringSettings from '@/components/settings/MonitoringSettings'

// В компоненте SettingsPage добавить новую секцию после других настроек:
{activeTab === 'monitoring' && (
  <MonitoringSettings />
)}
```

---

## 3️⃣ Unit и интеграционные тесты

**Приоритет:** 🟡 **СРЕДНИЙ**  
**Оценка времени:** 3-4 дня

### 3.1. Unit тесты для сервисов

#### 3.1.1. Тесты для SocialMediaExtractor (0.5 дня)

**Файл:** `backend/tests/unit/services/test_social_media_extractor.py`

**Тесты:**
- ✅ Извлечение соцсетей из meta tags
- ✅ Извлечение соцсетей из footer
- ✅ Извлечение соцсетей из contact page
- ✅ Нормализация URL
- ✅ Обработка ошибок парсинга

---

#### 3.1.2. Тесты для WebsiteStructureMonitor (0.5 дня)

**Файл:** `backend/tests/unit/services/test_website_structure_monitor.py`

**Тесты:**
- ✅ Захват снимка структуры сайта
- ✅ Извлечение ключевых страниц
- ✅ Сравнение снимков (детекция изменений)
- ✅ Обработка ошибок при недоступности сайта

---

#### 3.1.3. Тесты для MarketingChangeDetector (0.5 дня)

**Файл:** `backend/tests/unit/services/test_marketing_change_detector.py`

**Тесты:**
- ✅ Детекция изменений баннеров
- ✅ Детекция изменений цен
- ✅ Детекция новых продуктов
- ✅ Детекция новых вакансий
- ✅ Детекция изменений лендингов

---

#### 3.1.4. Тесты для SEOSignalCollector (0.5 дня)

**Файл:** `backend/tests/unit/services/test_seo_signal_collector.py`

**Тесты:**
- ✅ Сбор meta тегов
- ✅ Извлечение structured data
- ✅ Проверка robots.txt
- ✅ Проверка sitemap.xml
- ✅ Сравнение SEO сигналов

---

#### 3.1.5. Тесты для PressReleaseScraper (0.5 дня)

**Файл:** `backend/tests/unit/scrapers/test_press_release_scraper.py`

**Тесты:**
- ✅ Поиск страницы пресс-релизов
- ✅ Парсинг пресс-релизов
- ✅ Верификация страниц
- ✅ Обработка ошибок

---

#### 3.1.6. Тесты для Celery задач (0.5 дня)

**Файл:** `backend/tests/unit/tasks/test_observation_tasks.py`

**Тесты:**
- ✅ `discover_social_media_async()` - мокирование сервиса
- ✅ `capture_website_structure_async()` - мокирование сервиса
- ✅ `scrape_press_releases_async()` - мокирование скрапера
- ✅ `detect_marketing_changes_async()` - мокирование сервиса
- ✅ `collect_seo_signals_async()` - мокирование сервиса
- ✅ `build_monitoring_matrix_async()` - проверка формирования матрицы

---

### 3.2. Интеграционные тесты

#### 3.2.1. E2E тест онбординга (1 день)

**Файл:** `backend/tests/integration/api/test_onboarding_observation.py`

**Тесты:**
- ✅ Полный флоу настройки наблюдения через `/observation/setup`
- ✅ Проверка прогресса через `/observation/status`
- ✅ Проверка создания `CompetitorMonitoringMatrix`
- ✅ Проверка сохранения данных в матрице

---

#### 3.2.2. Тесты API endpoints мониторинга (0.5 дня)

**Файл:** `backend/tests/integration/api/test_monitoring_endpoints.py`

**Тесты:**
- ✅ `GET /monitoring/status` - получение статуса
- ✅ `GET /monitoring/matrix` - получение матрицы
- ✅ `GET /monitoring/stats` - получение статистики
- ✅ `GET /monitoring/changes` - получение изменений (новый endpoint)
- ✅ Проверка доступа (только свои компании)

---

## 4️⃣ API документация (Swagger)

**Приоритет:** 🟢 **НИЗКИЙ**  
**Оценка времени:** 1 день

### Задачи

#### 4.1. Улучшить документацию endpoints (0.5 дня)

**Файлы:**
- `backend/app/api/v1/endpoints/companies.py` - улучшить docstrings
- `backend/app/api/v1/endpoints/users.py` - добавить документацию для monitoring preferences

**Пример улучшения:**

```python
@router.get("/monitoring/changes")
async def get_monitoring_changes(
    company_ids: Optional[str] = Query(
        None, 
        description="Comma-separated list of company UUIDs to filter by"
    ),
    change_types: Optional[str] = Query(
        None,
        description="Comma-separated list of change types. "
                   "Valid types: website_structure, marketing_banner, "
                   "marketing_landing, marketing_product, marketing_jobs, "
                   "seo_meta, seo_structure, pricing"
    ),
    date_from: Optional[datetime] = Query(
        None,
        description="Filter events from this date (ISO 8601 format)"
    ),
    date_to: Optional[datetime] = Query(
        None,
        description="Filter events to this date (ISO 8601 format)"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Maximum number of results to return (1-500)"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Offset for pagination"
    ),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get monitoring change events for companies.
    
    This endpoint returns change events detected by the monitoring system,
    such as website structure changes, marketing updates, SEO changes, etc.
    
    **Access Control:**
    - Authenticated users can only see events for their own companies
    - Anonymous users can only see events for global companies (user_id is NULL)
    
    **Filtering:**
    - Filter by specific companies using `company_ids`
    - Filter by change types using `change_types`
    - Filter by date range using `date_from` and `date_to`
    
    **Pagination:**
    - Use `limit` to control page size (default: 50, max: 500)
    - Use `offset` for pagination (default: 0)
    - Response includes `total` count and `has_more` flag
    
    **Examples:**
    
    Get all changes for user's companies:
    ```bash
    GET /api/v1/companies/monitoring/changes
    ```
    
    Get only structure changes for specific companies:
    ```bash
    GET /api/v1/companies/monitoring/changes?company_ids=uuid1,uuid2&change_types=website_structure
    ```
    
    Get changes from last week:
    ```bash
    GET /api/v1/companies/monitoring/changes?date_from=2025-01-20T00:00:00Z
    ```
    
    **Response Format:**
    ```json
    {
      "events": [
        {
          "id": "uuid",
          "company_id": "uuid",
          "change_type": "website_structure",
          "change_summary": "Navigation menu updated",
          "detected_at": "2025-01-27T10:00:00Z",
          "source_url": "https://example.com",
          "details": {...}
        }
      ],
      "total": 100,
      "has_more": true
    }
    ```
    """
```

---

#### 4.2. Добавить примеры ответов в схемы (0.5 дня)

**Файл:** `backend/app/schemas/monitoring.py` (если создан) или в docstrings

**Примеры:**

```python
class MonitoringChangesResponseSchema(BaseModel):
    """
    Response schema for monitoring changes endpoint.
    
    Example:
    ```json
    {
      "events": [
        {
          "id": "550e8400-e29b-41d4-a716-446655440000",
          "company_id": "660e8400-e29b-41d4-a716-446655440000",
          "change_type": "website_structure",
          "change_summary": "Navigation menu updated - added 'Products' link",
          "detected_at": "2025-01-27T10:30:00Z",
          "source_url": "https://example.com",
          "details": {
            "type": "website_structure",
            "navigation_changes": {
              "added": ["/products"],
              "removed": []
            }
          }
        }
      ],
      "total": 42,
      "has_more": false
    }
    ```
    """
    events: List[MonitoringChangeEventSchema]
    total: int = Field(..., description="Total number of matching events")
    has_more: bool = Field(..., description="Whether there are more results")
```

---

#### 4.3. Проверить автоматическую генерацию Swagger (опционально)

FastAPI автоматически генерирует Swagger из docstrings и схем. Проверить:
- ✅ Все endpoints отображаются в `/docs`
- ✅ Все параметры описаны
- ✅ Примеры отображаются корректно
- ✅ Схемы данных корректны

**Файл:** `backend/main.py` - убедиться, что OpenAPI настройки корректны

---

## 📋 Итоговый план выполнения

### Этап 1: Критический endpoint (1-2 дня)
1. Реализовать `GET /monitoring/changes` endpoint
2. Добавить схемы Pydantic (опционально)
3. Протестировать endpoint

**Результат:** `MonitoringChangesTable` компонент начнет работать

---

### Этап 2: Настройки мониторинга (2-3 дня)
1. Расширить модель UserPreferences
2. Создать миграцию
3. Добавить API endpoints
4. Добавить Frontend компонент
5. Интегрировать в SettingsPage

**Результат:** Пользователи смогут настраивать мониторинг

---

### Этап 3: Тестирование (3-4 дня)
1. Unit тесты для сервисов (2 дня)
2. Unit тесты для задач (0.5 дня)
3. Интеграционные тесты (1.5 дня)

**Результат:** Стабильность системы, уверенность в изменениях

---

### Этап 4: Документация (1 день)
1. Улучшить docstrings
2. Добавить примеры
3. Проверить Swagger

**Результат:** Удобная документация для разработчиков

---

## ✅ Критерии готовности

### Endpoint `/monitoring/changes`
- [ ] Endpoint реализован и работает
- [ ] Поддерживает все фильтры (company_ids, change_types, dates)
- [ ] Пагинация работает корректно
- [ ] Контроль доступа реализован
- [ ] Тесты написаны и проходят

### Настройки мониторинга
- [ ] Модель расширена
- [ ] Миграция применена
- [ ] API endpoints работают
- [ ] Frontend компонент создан
- [ ] Интегрирован в SettingsPage

### Тесты
- [ ] Unit тесты для всех сервисов
- [ ] Unit тесты для Celery задач
- [ ] Интеграционные тесты для API
- [ ] Покрытие тестами >70%

### Документация
- [ ] Все endpoints документированы
- [ ] Примеры добавлены
- [ ] Swagger корректен

---

## 📝 Примечания

1. **Приоритет выполнения:**
   - Сначала реализовать критический endpoint `/monitoring/changes`
   - Затем настройки мониторинга
   - Тесты можно писать параллельно с разработкой
   - Документацию можно делать в последнюю очередь

2. **Зависимости:**
   - Endpoint `/monitoring/changes` не зависит от других задач
   - Настройки мониторинга не блокируют другие компоненты
   - Тесты можно писать параллельно

3. **Оценка времени:**
   - Минимальная: 8 дней (без улучшений документации)
   - Оптимальная: 10 дней (с хорошей документацией)
   - С запасом: 12 дней (с тщательным тестированием)

---

**Готовность к началу:** Все задачи детализированы, можно приступать к реализации.

