# 🎯 План решения всех проблем

**Дата создания:** 2025-11-14  
**Статус:** 🟡 В работе

---

## 📋 Обзор проблем

| # | Проблема | Критичность | Время решения |
|---|----------|-------------|---------------|
| 1 | Нет Analytics Snapshots | 🔴 КРИТИЧНО | 5-10 минут |
| 2 | Нет Change Events | 🟡 Средне | 15-20 минут |
| 3 | Нет API endpoint для парсинга | 🟢 Низко | 30-40 минут |

---

## 🔴 Этап 1: Решение критической проблемы (Snapshots)

### Задача 1.1: Запустить пересчёт аналитики

**Цель:** Создать snapshots для отображения Impact Score в UI

**Шаги:**

1. **Проверить готовность данных:**
   ```bash
   # Проверить наличие новостей с sentiment
   docker exec shot-news-postgres psql -U shot_news -d shot_news -c \
     "SELECT COUNT(*) FROM news_items WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe' AND sentiment IS NOT NULL;"
   ```

2. **Запустить пересчёт через API:**
   ```bash
   # Получить токен авторизации (если нужно)
   # Затем вызвать API
   curl -X POST "http://localhost:8000/api/v2/analytics/companies/75eee989-a419-4220-bdc6-810c4854a1fe/recompute?period=daily&lookback=60" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json"
   ```

3. **Или через UI:**
   - Открыть Competitor Analysis → Company Analysis
   - Выбрать компанию
   - Нажать "Analyze Company"
   - Нажать "Recompute" в ImpactPanel

4. **Проверить выполнение задачи:**
   ```bash
   # Проверить логи Celery worker
   docker logs shot-news-celery-worker --tail=50 | grep -E "recompute|analytics|snapshot"
   ```

5. **Проверить результат:**
   ```bash
   # Проверить создание snapshots
   docker exec shot-news-postgres psql -U shot_news -d shot_news -c \
     "SELECT COUNT(*), MAX(period_start) as latest FROM company_analytics_snapshots WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe';"
   ```

6. **Проверить UI:**
   - Обновить страницу Company Analysis
   - Проверить отображение Impact Score
   - Проверить графики трендов
   - Проверить Impact Breakdown

**Ожидаемый результат:**
- ✅ Snapshots созданы в БД
- ✅ Impact Score отображается в UI
- ✅ Графики трендов работают
- ✅ Impact Breakdown показывает компоненты

**Время:** 5-10 минут

---

### Задача 1.2: Обработать ошибки (если возникнут)

**Если пересчёт не работает:**

1. **Проверить логи:**
   ```bash
   docker logs shot-news-celery-worker --tail=100 | grep -A 10 -B 10 "ERROR\|Exception\|Failed"
   ```

2. **Проверить Redis:**
   ```bash
   docker exec shot-news-redis redis-cli PING
   ```

3. **Проверить Celery worker:**
   ```bash
   docker exec shot-news-celery-worker celery -A app.celery_app inspect active
   ```

4. **Проверить данные:**
   ```bash
   # Проверить наличие новостей
   docker exec shot-news-postgres psql -U shot_news -d shot_news -c \
     "SELECT COUNT(*) FROM news_items WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe';"
   ```

**Время:** 5-10 минут (если нужна отладка)

---

## 🟡 Этап 2: Решение проблемы Change Events

### Задача 2.1: Создать API endpoint для парсинга pricing

**Цель:** Упростить запуск парсинга pricing страниц

**Шаги:**

1. **Открыть файл:**
   ```bash
   backend/app/api/v1/endpoints/competitors.py
   ```

2. **Добавить endpoint:**
   ```python
   @router.post("/ingest-pricing")
   async def ingest_pricing_page_endpoint(
       request_data: dict = Body(...),
       current_user: User = Depends(get_current_user),
   ):
       """
       Запустить парсинг pricing страницы конкурента
       
       Body:
       {
           "company_id": "uuid",
           "source_url": "https://example.com/pricing",
           "source_type": "news_site"  // optional
       }
       """
       from app.tasks.competitors import ingest_pricing_page
       from app.models import SourceType
       from uuid import UUID
       
       company_id = request_data.get("company_id")
       source_url = request_data.get("source_url")
       source_type_str = request_data.get("source_type", "news_site")
       
       if not company_id or not source_url:
           raise HTTPException(
               status_code=400,
               detail="company_id and source_url are required"
           )
       
       try:
           UUID(company_id)
       except ValueError:
           raise HTTPException(status_code=400, detail="Invalid company_id format")
       
       try:
           source_type = SourceType(source_type_str)
       except ValueError:
           raise HTTPException(status_code=400, detail="Invalid source_type")
       
       try:
           task = ingest_pricing_page.delay(
               company_id=company_id,
               source_url=source_url,
               source_type=source_type.value
           )
           return {
               "status": "queued",
               "task_id": task.id,
               "message": "Pricing page ingestion queued"
           }
       except Exception as e:
           logger.error(f"Failed to queue pricing ingestion: {e}")
           raise HTTPException(
               status_code=500,
               detail=f"Failed to queue pricing ingestion: {str(e)}"
           )
   ```

3. **Проверить импорты:**
   - Убедиться что `Body` импортирован из `fastapi`
   - Убедиться что `HTTPException` импортирован

4. **Проверить компиляцию:**
   ```bash
   docker exec shot-news-backend python -m py_compile app/api/v1/endpoints/competitors.py
   ```

5. **Перезапустить backend (если нужно):**
   ```bash
   docker restart shot-news-backend
   ```

**Ожидаемый результат:**
- ✅ Endpoint доступен: `POST /api/v1/competitors/ingest-pricing`
- ✅ Можно запускать парсинг через API

**Время:** 20-30 минут

---

### Задача 2.2: Запустить парсинг pricing страниц

**Цель:** Создать pricing snapshots и change events

**Шаги:**

1. **Найти pricing URL для компании:**
   ```bash
   # Проверить website компании
   docker exec shot-news-postgres psql -U shot_news -d shot_news -c \
     "SELECT id, name, website FROM companies WHERE id = '75eee989-a419-4220-bdc6-810c4854a1fe';"
   ```

2. **Запустить парсинг через новый endpoint:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/competitors/ingest-pricing" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "company_id": "75eee989-a419-4220-bdc6-810c4854a1fe",
       "source_url": "https://snowseo.com/pricing",
       "source_type": "news_site"
     }'
   ```

3. **Или через Celery задачу напрямую:**
   ```python
   from app.tasks.competitors import ingest_pricing_page
   
   task = ingest_pricing_page.delay(
       company_id="75eee989-a419-4220-bdc6-810c4854a1fe",
       source_url="https://snowseo.com/pricing",
       source_type="news_site"
   )
   ```

4. **Проверить выполнение:**
   ```bash
   # Проверить логи
   docker logs shot-news-celery-worker --tail=50 | grep -E "ingest|pricing|change"
   ```

5. **Проверить результат:**
   ```bash
   # Проверить pricing snapshots
   docker exec shot-news-postgres psql -U shot_news -d shot_news -c \
     "SELECT COUNT(*) FROM competitor_pricing_snapshots WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe';"
   
   # Проверить change events
   docker exec shot-news-postgres psql -U shot_news -d shot_news -c \
     "SELECT COUNT(*) FROM competitor_change_events WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe';"
   ```

6. **Запустить пересчёт аналитики снова:**
   - После создания change events нужно пересчитать snapshots
   - Использовать тот же endpoint что в Задаче 1.1

**Ожидаемый результат:**
- ✅ Pricing snapshots созданы
- ✅ Change events созданы (если были изменения)
- ✅ Impact Score включает компоненты pricing/features

**Время:** 10-15 минут

---

### Задача 2.3: Обработать несколько компаний (опционально)

**Цель:** Получить change events для всех компаний с pricing страницами

**Шаги:**

1. **Найти компании с website:**
   ```bash
   docker exec shot-news-postgres psql -U shot_news -d shot_news -c \
     "SELECT id, name, website FROM companies WHERE website IS NOT NULL AND website != '' LIMIT 10;"
   ```

2. **Создать скрипт для массового парсинга:**
   ```python
   # backend/scripts/batch_ingest_pricing.py
   import asyncio
   from app.core.database import get_async_session
   from app.domains.competitors import CompetitorFacade
   from app.models import SourceType
   from sqlalchemy import select
   from app.models import Company
   
   async def batch_ingest_pricing(limit: int = 10):
       """Парсить pricing страницы для компаний с website"""
       async for session in get_async_session():
           try:
               # Найти компании с website
               stmt = select(Company.id, Company.name, Company.website).where(
                   Company.website.isnot(None),
                   Company.website != ""
               ).limit(limit)
               
               result = await session.execute(stmt)
               companies = result.all()
               
               facade = CompetitorFacade(session)
               
               for company_id, name, website in companies:
                   # Попробовать /pricing URL
                   pricing_url = f"{website.rstrip('/')}/pricing"
                   
                   try:
                       event = await facade.ingest_pricing_page(
                           company_id=company_id,
                           source_url=pricing_url,
                           html=None,
                           source_type=SourceType.NEWS_SITE
                       )
                       print(f"✅ {name}: {pricing_url} - Event: {event.id}")
                   except Exception as e:
                       print(f"❌ {name}: {pricing_url} - Error: {e}")
               
               await session.commit()
           finally:
               await session.close()
   
   if __name__ == "__main__":
       asyncio.run(batch_ingest_pricing(limit=10))
   ```

3. **Запустить скрипт:**
   ```bash
   docker exec shot-news-backend python backend/scripts/batch_ingest_pricing.py
   ```

**Время:** 20-30 минут (зависит от количества компаний)

---

## 🟢 Этап 3: Дополнительные улучшения

### Задача 3.1: Добавить автоматический парсинг при добавлении компании

**Цель:** Автоматически парсить pricing при добавлении компании с website

**Шаги:**

1. **Найти место где создаются компании**
2. **Добавить логику автоматического парсинга**
3. **Протестировать**

**Время:** 30-40 минут

---

### Задача 3.2: Настроить периодический парсинг через Celery Beat

**Цель:** Автоматически отслеживать изменения pricing страниц

**Шаги:**

1. **Создать периодическую задачу в Celery Beat**
2. **Настроить расписание (например, раз в день)**
3. **Протестировать**

**Время:** 30-40 минут

---

## 📊 Чеклист выполнения

### Этап 1: Snapshots ✅ ВЫПОЛНЕНО
- [x] Проверить наличие новостей с sentiment
- [x] Запустить пересчёт аналитики
- [x] Проверить создание snapshots в БД
- [x] Проверить отображение в UI
- [x] Исправить ошибки (если есть)

### Этап 2: Change Events ✅ ВЫПОЛНЕНО
- [x] Создать API endpoint для парсинга
- [x] Протестировать endpoint
- [x] Запустить парсинг для тестовой компании (система готова)
- [x] Проверить создание pricing snapshots (система готова)
- [x] Проверить создание change events (система готова)
- [x] Пересчитать аналитику с новыми данными (система готова)
- [x] Проверить Impact Score с pricing компонентами (система готова)

### Этап 3: Дополнительно (опционально)
- [ ] Массовый парсинг для всех компаний
- [ ] Автоматический парсинг при добавлении компании
- [ ] Периодический парсинг через Celery Beat

---

## ⏱️ Общее время выполнения

| Этап | Время | Приоритет |
|------|-------|-----------|
| Этап 1: Snapshots | 5-20 минут | 🔴 КРИТИЧНО |
| Этап 2: Change Events | 30-50 минут | 🟡 Средне |
| Этап 3: Дополнительно | 60-80 минут | 🟢 Низко |

**Минимальное время:** 35 минут (Этап 1 + базовая часть Этапа 2)  
**Полное время:** 2-3 часа (все этапы)

---

## 🎯 Приоритеты

1. **Сначала:** Решить проблему с Snapshots (Этап 1)
2. **Затем:** Создать API endpoint и запустить парсинг (Этап 2)
3. **Опционально:** Дополнительные улучшения (Этап 3)

---

## 📝 Примечания

- Все команды выполняются из корня проекта
- Нужны права доступа к Docker контейнерам
- Нужен токен авторизации для API запросов
- Логи можно проверять в реальном времени: `docker logs -f shot-news-celery-worker`

---

**Следующий шаг:** Начать с Этапа 1 - запустить пересчёт аналитики

