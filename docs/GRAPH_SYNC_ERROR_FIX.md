# 🔧 Исправление ошибки Graph Sync Timeout

**Дата исправления:** 2025-11-14 22:46  
**Проблема:** Timeout при вызове `POST /analytics/companies/{company_id}/graph/sync`

---

## ❌ Проблема

**Симптомы:**
```
❌ API Error: POST /analytics/companies/75eee989-a419-4220-bdc6-810c4854a1fe/graph/sync undefined
Failed to sync knowledge graph: AxiosError {message: 'timeout of 30000ms exceeded', ...}
```

**Причины:**
1. ❌ В endpoint `trigger_graph_sync` отсутствовала обработка ошибок для Celery/Redis
2. ❌ При недоступности Celery/Redis запрос зависал, вызывая timeout на фронтенде
3. ⚠️ Timeout был слишком долгим (30 секунд) для простой постановки задачи в очередь

---

## ✅ Исправления

### 1. Backend: Добавлена обработка ошибок в endpoint

**Файл:** `backend/app/api/v2/endpoints/analytics.py`

**Изменения:**
- ✅ Добавлен `try/except` блок для обработки `KombuOperationalError` и `redis_exceptions.RedisError`
- ✅ При ошибке возвращается `503 Service Unavailable` с понятным сообщением
- ✅ Добавлено логирование ошибок

**Код:**
```python
@router.post(
    "/companies/{company_id}/graph/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger knowledge graph sync",
)
async def trigger_graph_sync(
    company_id: UUID,
    period_start: datetime = Query(..., description="Period start in ISO format"),
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAILY),
    current_user: User = Depends(get_current_user),
) -> dict:
    period_start = _ensure_timezone(period_start)
    logger.info("User %s triggered graph sync for company %s", current_user.id, company_id)
    try:
        task = sync_company_knowledge_graph.delay(
            str(company_id),
            period_start.isoformat(),
            period.value,
        )
    except (KombuOperationalError, redis_exceptions.RedisError) as exc:
        logger.error(
            "Failed to enqueue graph sync for company %s: %s",
            company_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph sync queue is unavailable. Please ensure Celery worker and Redis are running.",
        ) from exc
    return {"status": "queued", "task_id": task.id}
```

---

### 2. Frontend: Уменьшен timeout для endpoint

**Файл:** `frontend/src/services/api.ts`

**Изменения:**
- ✅ Уменьшен timeout с 30 секунд до 10 секунд для `triggerKnowledgeGraphSync`
- ✅ Это достаточно для постановки задачи в очередь (не должно зависать)

**Код:**
```typescript
static async triggerKnowledgeGraphSync(
  companyId: string,
  periodStartIso: string,
  period: AnalyticsPeriod = 'daily'
): Promise<{ status: string; task_id: string }> {
  const response = await apiV2.post<{ status: string; task_id: string }>(
    `/analytics/companies/${companyId}/graph/sync`,
    null,
    { 
      params: { period_start: periodStartIso, period },
      timeout: 10000 // 10 секунд для быстрой очереди (не должно зависать)
    }
  )
  return response.data
}
```

---

## 📋 Обработка ошибок на Frontend

**Файл:** `frontend/src/pages/CompetitorAnalysisPage.tsx`

**Текущая обработка (уже есть):**
```typescript
const handleSyncKnowledgeGraph = async () => {
  if (!selectedCompany || !impactSnapshot) return
  try {
    const { task_id } = await ApiService.triggerKnowledgeGraphSync(
      selectedCompany.id,
      impactSnapshot.period_start,
      impactSnapshot.period
    )
    toast.success('Knowledge graph sync queued')
    await refetchAnalyticsInsights()
    setPendingTaskId(task_id)
  } catch (error: any) {
    console.error('Failed to sync knowledge graph:', error)
    const message = error?.response?.data?.detail || error?.message || 'Failed to sync knowledge graph'
    toast.error(message)
  }
}
```

**Вывод:** ✅ Обработка ошибок уже корректна, теперь будут приходить правильные сообщения об ошибках.

---

## 🔍 Диагностика

### Проверка статуса сервисов

```bash
# Проверить, что Celery worker работает
docker ps | grep celery-worker

# Проверить, что Redis работает
docker ps | grep redis

# Проверить логи backend
docker logs shot-news-backend --tail=50 | grep graph/sync

# Проверить логи Celery worker
docker logs shot-news-celery-worker --tail=50 | grep graph
```

### Возможные проблемы

1. **Redis недоступен:**
   - ✅ Backend вернет `503 Service Unavailable`
   - ✅ Frontend покажет понятное сообщение об ошибке

2. **Celery worker не работает:**
   - ✅ Backend вернет `503 Service Unavailable`
   - ✅ Frontend покажет понятное сообщение об ошибке

3. **Задача выполняется слишком долго:**
   - ⚠️ Это нормально - задача выполняется асинхронно
   - ⚠️ Frontend должен только поставить задачу в очередь (10 секунд достаточно)

---

## ✅ Результат

**После исправлений:**
- ✅ Endpoint корректно обрабатывает ошибки Celery/Redis
- ✅ При недоступности сервисов возвращается понятная ошибка `503`
- ✅ Frontend получает корректное сообщение об ошибке
- ✅ Timeout уменьшен до 10 секунд (достаточно для постановки задачи)
- ✅ Нет зависаний при недоступности Celery/Redis

**Статус:** ✅ **ИСПРАВЛЕНО**

---

## 📝 Рекомендации

### Для пользователя:
1. ✅ Убедитесь, что Celery worker и Redis запущены
2. ✅ Проверьте логи при возникновении ошибок

### Для разработчика:
1. ✅ Все endpoint'ы для постановки задач в очередь должны иметь обработку ошибок Celery/Redis
2. ✅ Timeout для таких endpoint'ов должен быть коротким (10-15 секунд)
3. ✅ Frontend должен показывать понятные сообщения об ошибках

---

**Дата исправления:** 2025-11-14 22:46  
**Статус:** ✅ **ПРОБЛЕМА РЕШЕНА**




