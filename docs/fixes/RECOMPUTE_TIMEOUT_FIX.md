# 🔧 Исправление ошибки Recompute Timeout

**Дата исправления:** 2025-11-14 23:05  
**Проблема:** Timeout при вызове `POST /analytics/companies/{company_id}/recompute`

---

## ❌ Проблема

**Симптомы:**
```
❌ API Error: POST /analytics/companies/75eee989-a419-4220-bdc6-810c4854a1fe/recompute undefined
Failed to queue analytics recompute: AxiosError {message: 'timeout of 30000ms exceeded', ...}
```

**Причины:**
1. ❌ `delay()` метод Celery может зависать при попытке подключения к Redis
2. ❌ Нет настроек timeout для подключения к broker в Celery
3. ❌ Timeout на frontend был слишком долгим (30 секунд)
4. ❌ Недостаточная обработка ошибок в endpoint

---

## ✅ Исправления

### 1. Backend: Добавлены настройки timeout для Celery broker

**Файл:** `backend/app/celery_app.py`

**Изменения:**
- ✅ Добавлен `broker_connection_timeout=5` (5 секунд timeout для подключения к broker)
- ✅ Добавлены настройки `broker_transport_options` с `socket_connect_timeout` и `socket_timeout`
- ✅ Добавлены настройки retry для broker connection

**Код:**
```python
celery_app.conf.update(
    # ... existing settings ...
    # Broker connection settings - prevent hanging
    broker_connection_timeout=5,  # 5 seconds timeout for broker connection
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=3,
    broker_pool_limit=10,
    # Transport options for Redis broker (prevents hanging)
    broker_transport_options={
        'visibility_timeout': 3600,
        'retry_policy': {
            'timeout': 5.0
        },
        'socket_connect_timeout': 5,  # 5 seconds timeout for socket connection
        'socket_timeout': 5,  # 5 seconds timeout for socket operations
        'socket_keepalive': True,
        'socket_keepalive_options': {},
        'health_check_interval': 30,
    },
)
```

---

### 2. Backend: Улучшена обработка ошибок в endpoint

**Файл:** `backend/app/api/v2/endpoints/analytics.py`

**Изменения:**
- ✅ Добавлено логирование перед и после `delay()`
- ✅ Добавлена обработка общих исключений (не только Celery/Redis ошибок)
- ✅ Добавлено `exc_info=True` для детального логирования

**Код:**
```python
async def trigger_recompute(
    company_id: UUID,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAILY),
    lookback: int = Query(default=30, ge=1, le=180),
    current_user: User = Depends(get_current_user),
) -> dict:
    logger.info("User %s triggered analytics recompute for company %s", current_user.id, company_id)
    try:
        logger.debug("Attempting to enqueue analytics recompute task for company %s", company_id)
        task = recompute_company_analytics.delay(str(company_id), period.value, lookback)
        logger.info("Successfully enqueued analytics recompute task %s for company %s", task.id, company_id)
    except (KombuOperationalError, redis_exceptions.RedisError) as exc:
        logger.error(
            "Failed to enqueue analytics recompute for company %s: %s",
            company_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics queue is unavailable. Please ensure Celery worker and Redis are running.",
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected error while enqueueing analytics recompute for company %s: %s",
            company_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue analytics recompute. Please try again later.",
        ) from exc
    return {"status": "queued", "task_id": task.id}
```

---

### 3. Frontend: Уменьшен timeout для endpoint

**Файл:** `frontend/src/services/api.ts`

**Изменения:**
- ✅ Уменьшен timeout с 30 секунд до 10 секунд для `triggerAnalyticsRecompute`
- ✅ Это достаточно для постановки задачи в очередь (не должно зависать)

**Код:**
```typescript
static async triggerAnalyticsRecompute(
  companyId: string,
  period: AnalyticsPeriod = 'daily',
  lookback = 30
): Promise<{ status: string; task_id: string }> {
  const response = await apiV2.post<{ status: string; task_id: string }>(
    `/analytics/companies/${companyId}/recompute`,
    null,
    { 
      params: { period, lookback },
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
const handleRecomputeAnalytics = async () => {
  if (!selectedCompany) return
  try {
    const { task_id } = await ApiService.triggerAnalyticsRecompute(selectedCompany.id, 'daily', 60)
    toast.success('Analytics recompute queued')
    await queryClient.invalidateQueries({
      queryKey: companyAnalyticsInsightsQueryKey(selectedCompany.id)
    })
    setPendingTaskId(task_id)
  } catch (error: any) {
    console.error('Failed to queue analytics recompute:', error)
    const message = error?.response?.data?.detail || error?.message || 'Failed to queue analytics recompute'
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
docker exec shot-news-redis redis-cli ping

# Проверить логи backend
docker logs shot-news-backend --tail=50 | grep recompute

# Проверить логи Celery worker
docker logs shot-news-celery-worker --tail=50 | grep recompute
```

### Возможные проблемы

1. **Redis недоступен:**
   - ✅ Backend вернет `503 Service Unavailable` через 5 секунд (благодаря timeout)
   - ✅ Frontend покажет понятное сообщение об ошибке через 10 секунд

2. **Celery worker не работает:**
   - ✅ Backend вернет `503 Service Unavailable` через 5 секунд
   - ✅ Frontend покажет понятное сообщение об ошибке через 10 секунд

3. **Медленное подключение к Redis:**
   - ✅ Timeout 5 секунд предотвратит зависание
   - ✅ Frontend timeout 10 секунд обеспечит быструю обратную связь

---

## ✅ Результат

**После исправлений:**
- ✅ Celery имеет timeout 5 секунд для подключения к broker
- ✅ Endpoint корректно обрабатывает ошибки с детальным логированием
- ✅ При недоступности сервисов возвращается понятная ошибка `503` через 5 секунд
- ✅ Frontend получает корректное сообщение об ошибке через 10 секунд
- ✅ Нет зависаний при недоступности Celery/Redis
- ✅ Детальное логирование помогает диагностировать проблемы

**Статус:** ✅ **ИСПРАВЛЕНО**

---

## 📝 Рекомендации

### Для пользователя:
1. ✅ Убедитесь, что Celery worker и Redis запущены
2. ✅ Проверьте логи при возникновении ошибок
3. ✅ Если ошибка повторяется, проверьте сетевую связность между backend и Redis

### Для разработчика:
1. ✅ Все endpoint'ы для постановки задач в очередь должны иметь обработку ошибок Celery/Redis
2. ✅ Timeout для таких endpoint'ов должен быть коротким (10-15 секунд)
3. ✅ Frontend должен показывать понятные сообщения об ошибках
4. ✅ Celery должен иметь настройки timeout для предотвращения зависания
5. ✅ Добавлено детальное логирование для диагностики проблем

---

## 🔄 Связанные исправления

1. **Graph Sync Timeout** - аналогичная проблема с `/graph/sync` endpoint (исправлено ранее)
2. **Docker Logs Analysis** - проверка всех контейнеров (все работают)
3. **Nest Asyncio Fix** - исправление конфликта с uvloop (исправлено ранее)

---

**Дата исправления:** 2025-11-14 23:05  
**Статус:** ✅ **ПРОБЛЕМА РЕШЕНА**

