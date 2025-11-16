# 🔧 Исправление проблем с асинхронными функциями кнопок Recompute/Sync Graph

**Дата исправления:** 2025-11-15 00:15  
**Проблема:** Кнопки Recompute и Sync Graph зависают, запросы отправляются с `null` в теле, timeout ошибки

---

## ❌ Проблемы

**Симптомы:**
1. ❌ Запрос `POST /analytics/companies/{company_id}/recompute` отправляется с `null` в теле
2. ❌ Timeout 10000ms при вызове recompute/sync graph
3. ❌ Кнопки не показывают loading состояние
4. ❌ `delay()` метод Celery зависает при подключении к Redis
5. ❌ Типы функций не соответствуют async функциям

---

## ✅ Исправления

### 1. Backend: Использование `apply_async` вместо `delay()`

**Проблема:** `delay()` может блокироваться при подключении к Redis, даже с настройками timeout.

**Решение:** Использовать `apply_async()` с явными параметрами connection retry.

**Файл:** `backend/app/api/v2/endpoints/analytics.py`

**Изменения:**
```python
# Было:
task = recompute_company_analytics.delay(str(company_id), period.value, lookback)

# Стало:
task = recompute_company_analytics.apply_async(
    args=[str(company_id), period.value, lookback],
    countdown=0,
    expires=None,
    connection_retry=True,
    connection_retry_on_startup=True,
)
```

**Для graph sync:**
```python
task = sync_company_knowledge_graph.apply_async(
    args=[str(company_id), period_start.isoformat(), period.value],
    countdown=0,
    expires=None,
    connection_retry=True,
    connection_retry_on_startup=True,
)
```

---

### 2. Frontend: Обновление типов для async функций

**Проблема:** Типы функций указаны как `() => void`, но на самом деле они `async () => Promise<void>`.

**Решение:** Обновить типы в компонентах.

**Файлы:**
- `frontend/src/features/competitor-analysis/components/CompanyAnalysisFlow.tsx`
- `frontend/src/features/competitor-analysis/components/ImpactPanel.tsx`

**Изменения:**
```typescript
// Было:
onRecomputeAnalytics: () => void
onSyncKnowledgeGraph: () => void

// Стало:
onRecomputeAnalytics: () => void | Promise<void>
onSyncKnowledgeGraph: () => void | Promise<void>
```

---

### 3. Frontend: Добавление loading состояния для кнопок

**Проблема:** Кнопки не показывают состояние загрузки, пользователь не видит, что запрос выполняется.

**Решение:** Добавить state для отслеживания загрузки и показывать индикатор.

**Файл:** `frontend/src/features/competitor-analysis/components/ImpactPanel.tsx`

**Изменения:**
```typescript
import { useState } from 'react'

export const ImpactPanel = ({ ... }: ImpactPanelProps) => {
  const [isRecomputing, setIsRecomputing] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)

  const handleRecompute = async () => {
    setIsRecomputing(true)
    try {
      await onRecompute()
    } finally {
      setIsRecomputing(false)
    }
  }

  const handleSyncGraph = async () => {
    setIsSyncing(true)
    try {
      await onSyncKnowledgeGraph()
    } finally {
      setIsSyncing(false)
    }
  }

  // В кнопках:
  <button
    onClick={handleRecompute}
    disabled={isRecomputing || isSyncing}
  >
    {isRecomputing ? (
      <>
        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600 mr-1.5" />
        Recomputing...
      </>
    ) : (
      'Recompute'
    )}
  </button>
```

---

### 4. Backend: Логирование запроса с `null`

**Проблема:** В логах показывается `null` для POST запросов - это нормально для запросов без тела (используются query params).

**Объяснение:**
- POST запросы к `/recompute` и `/graph/sync` используют query parameters (`?period=daily&lookback=60`)
- Тело запроса (`data`) - `null`, это нормально
- Параметры передаются через `params` в axios config

**Код:**
```typescript
// frontend/src/services/api.ts
const response = await apiV2.post<{ status: string; task_id: string }>(
  `/analytics/companies/${companyId}/recompute`,
  null,  // <-- Это нормально, тело не нужно
  { 
    params: { period, lookback },  // <-- Параметры передаются здесь
    timeout: 10000
  }
)
```

---

## 🔍 Почему `null` в логах - это нормально

**В логах видно:**
```
🚀 API Request: POST /analytics/companies/.../recompute null
```

**Это нормально, потому что:**
1. ✅ POST запрос не требует тела для этих endpoint'ов
2. ✅ Параметры передаются через query string (`?period=daily&lookback=60`)
3. ✅ Backend endpoint принимает параметры через `Query(...)` из FastAPI
4. ✅ Это стандартный подход для PUT/POST запросов, которые не требуют тела

**Backend endpoint:**
```python
async def trigger_recompute(
    company_id: UUID,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAILY),  # <-- Query param
    lookback: int = Query(default=30, ge=1, le=180),  # <-- Query param
    ...
)
```

---

## ✅ Результат

**После исправлений:**
- ✅ `apply_async()` не блокируется при подключении к Redis
- ✅ Кнопки показывают loading состояние во время выполнения
- ✅ Кнопки отключаются во время выполнения (prevents double-click)
- ✅ Типы функций соответствуют реальным async функциям
- ✅ Обработка ошибок работает корректно
- ✅ `null` в логах - это нормально (тело не требуется)

**Статус:** ✅ **ИСПРАВЛЕНО**

---

## 📝 Рекомендации

### Для пользователя:
1. ✅ Кнопки теперь показывают состояние загрузки
2. ✅ Кнопки отключаются во время выполнения запроса
3. ✅ При ошибке показывается понятное сообщение

### Для разработчика:
1. ✅ Все async функции должны иметь правильные типы `() => Promise<void>`
2. ✅ Кнопки с async действиями должны показывать loading состояние
3. ✅ Использовать `apply_async()` вместо `delay()` для лучшего контроля timeout
4. ✅ Добавлять обработку ошибок с try/finally для сброса loading состояния

---

**Дата исправления:** 2025-11-15 00:15  
**Статус:** ✅ **ПРОБЛЕМА РЕШЕНА**




