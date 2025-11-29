# Почему нет Snapshots и Change Events?

## 📊 Текущее состояние

| Тип данных | Количество | Причина отсутствия |
|------------|------------|-------------------|
| **Company Analytics Snapshots** | 0 | ⏳ Пересчёт аналитики ещё не запускался |
| **Competitor Change Events** | 0 | ℹ️ Нет данных о pricing страницах конкурентов |
| **Competitor Pricing Snapshots** | 0 | ℹ️ Не парсились pricing страницы |

---

## 1. Почему нет Snapshots (company_analytics_snapshots)?

### Причина
**Snapshots создаются только при запуске пересчёта аналитики.**

Snapshots НЕ создаются автоматически при добавлении новостей. Они создаются только когда:
1. Пользователь нажимает кнопку **"Recompute"** в UI
2. Или вызывается API endpoint `/api/v2/analytics/companies/{id}/recompute`
3. Или запускается Celery задача `recompute_company_analytics`

### Как создаются Snapshots

```python
# backend/app/domains/analytics/services/snapshot_service.py

async def compute_snapshot_for_period(
    self,
    company_id: UUID,
    period_start: datetime,
    period: AnalyticsPeriod,
) -> CompanyAnalyticsSnapshot:
    """Создаёт snapshot для указанного периода."""
    # 1. Агрегирует новости за период
    news_metrics = await self._aggregate_news(company_id, period_start, period_end)
    
    # 2. Загружает change events (если есть)
    changes = await self._load_change_events(company_id, period_start, period_end)
    
    # 3. Вычисляет компоненты Impact Score
    components = await self._build_components(...)
    
    # 4. Сохраняет snapshot в БД
    return await self._snapshot_repo.create_snapshot(...)
```

### Что нужно сделать
✅ **Запустить пересчёт аналитики:**
- Через UI: Нажать "Recompute" в ImpactPanel
- Или через API: `POST /api/v2/analytics/companies/{id}/recompute`

**После пересчёта snapshots появятся автоматически!**

---

## 2. Почему нет Change Events (competitor_change_events)?

### ✅ Парсеры ЕСТЬ и работают!

**Парсеры для pricing страниц реализованы:**
- ✅ `PricingPageParser` в `backend/app/parsers/pricing.py` - полноценный парсер
- ✅ `CompetitorIngestionDomainService` - сервис для парсинга
- ✅ Celery задача `ingest_pricing_page` - для асинхронного парсинга

### Причина отсутствия Change Events
**Change Events создаются только при парсинге pricing страниц конкурентов.**

Change Events НЕ связаны с новостями напрямую. Они создаются когда:
1. Парсится pricing страница конкурента (например, `/pricing`)
2. Обнаруживаются изменения в pricing или features
3. Сравнивается новый snapshot с предыдущим

**НО:** Парсинг pricing страниц нужно запускать вручную (через Celery задачу или API endpoint).

### Как создаются Change Events

```python
# backend/app/domains/competitors/services/ingestion_service.py

async def ingest_pricing_page(
    self,
    company_id: UUID,
    source_url: str,
    html: str,
    source_type: SourceType,
):
    """Парсит pricing страницу и создаёт change event если есть изменения."""
    # 1. Парсит HTML страницы
    parse_result = self._parser.parse(html)
    
    # 2. Сравнивает с предыдущим snapshot
    diff = self._compare_with_previous(...)
    
    # 3. Создаёт новый pricing snapshot
    snapshot = await self._snapshot_repo.create_snapshot(...)
    
    # 4. Создаёт change event если есть изменения
    event = await self._change_service.create_change_event(
        company_id=company_id,
        diff=diff,
        ...
    )
```

### Текущее состояние
- **Competitor Pricing Snapshots**: 0 (не парсились pricing страницы)
- **Change Events**: 0 (нет данных для сравнения)

### Это критично?
❌ **НЕТ, не критично для аналитики новостей!**

Change Events используются в аналитике как **дополнительный источник данных**:
- Они добавляют компонент "Pricing Changes" и "Feature Updates" в Impact Score
- Они создают связи в Knowledge Graph между событиями и новостями
- Но аналитика новостей работает и без них!

### Как получить Change Events

**Вариант 1: Через Celery задачу (рекомендуется)**
```python
from app.tasks.competitors import ingest_pricing_page

# Запустить парсинг pricing страницы
task = ingest_pricing_page.delay(
    company_id="75eee989-a419-4220-bdc6-810c4854a1fe",
    source_url="https://snowseo.com/pricing",  # или другой URL
    source_type="news_site"
)
```

**Вариант 2: Через API (если endpoint создан)**
```bash
POST /api/v1/competitors/ingest-pricing
{
  "company_id": "75eee989-a419-4220-bdc6-810c4854a1fe",
  "source_url": "https://snowseo.com/pricing"
}
```

**Вариант 3: Напрямую через сервис**
```python
from app.domains.competitors import CompetitorFacade

facade = CompetitorFacade(session)
event = await facade.ingest_pricing_page(
    company_id=company_id,
    source_url="https://snowseo.com/pricing",
    html=None,  # будет загружен автоматически
    source_type=SourceType.NEWS_SITE
)
```

**Примечание:** API endpoint для запуска парсинга может отсутствовать - нужно создать или использовать Celery задачу напрямую.

---

## 3. Влияние на Impact Score

### Без Change Events
Impact Score вычисляется из 5 компонентов:
1. ✅ **News Volume** (объём новостей) - работает
2. ✅ **Sentiment** (сентимент) - работает
3. ✅ **Priority** (приоритет) - работает
4. ⚠️ **Pricing Changes** - будет 0 (нет change events)
5. ⚠️ **Feature Updates** - будет 0 (нет change events)

**Итог:** Impact Score будет вычислен, но без компонентов pricing/features.

### С Change Events
Все 5 компонентов будут заполнены, Impact Score будет более точным.

---

## ✅ Резюме

### Snapshots (company_analytics_snapshots)
- ❌ **Нет** потому что пересчёт не запускался
- ✅ **Решение:** Запустить пересчёт через UI или API
- ⏱️ **Время:** 5-10 секунд после запуска

### Change Events (competitor_change_events)
- ❌ **Нет** потому что нет данных о pricing страницах
- ℹ️ **Это нормально** - не критично для аналитики новостей
- ✅ **Решение (опционально):** Добавить и парсить pricing страницы конкурентов

---

## 🎯 Что делать сейчас?

### Обязательно:
1. ✅ **Запустить пересчёт аналитики** для создания snapshots
   - Через UI: "Recompute" в ImpactPanel
   - Или через API: `POST /api/v2/analytics/companies/{id}/recompute`

### Опционально (для полной функциональности):
2. ⚠️ **Добавить pricing страницы** конкурентов (если нужны Change Events)
3. ⚠️ **Запустить парсинг** pricing страниц

---

**Вывод:** Отсутствие snapshots - это нормально до первого пересчёта. Отсутствие change events - это нормально, если не парсятся pricing страницы. Оба не блокируют работу системы!

