# Phase 2 — Competitor Intelligence Refactor Plan

Дата: 2025-11-10  
Подготовил: GPT-5 Codex

---

## 1. Цель
Перестроить модуль Competitor Intelligence (сканирование конкурентов, change log, pricing snapshots) в соответствии с новой доменной архитектурой:
- выделить bounded context `app/domains/competitors`;
- разделить ingestion (scraping/snapshots), анализ изменений и API фасады;
- уменьшить заимствования из news-домена и обеспечить повторное использование общих сервисов (NLP, analytics).

## 2. Текущее состояние
- **Сервисы:**  
  - `app/services/competitor_service.py`: смешивает CRUD, сканирование, агрегации.  
  - `app/services/competitor_change_service.py`: обработка pricing change diff, генерация `CompetitorChangeEvent`.  
  - `app/services/nlp_service.py` частично используется для описаний (непрямо).
- **API:**  
  - `app/api/v1/endpoints/competitors.py`, `companies.py`, `products.py` (частично).  
  - `app/api/v1/endpoints/notifications.py` использует change events.
- **Celery:**  
  - `app/tasks/scraping.py` содержит вспомогательные задачи по конкурентам (seed, digests).  
  - `app/tasks/notifications.py` ссылается на change events.
- **Модели:**  
  - `app/models/competitor.py`, `app/models/notification_channels.py`, `app/models/products.py`.
- **Проблемы:** бизнес-логика размазана между сервисами, API и Celery; отсутствуют фасады, сложно тестировать кусочно.

## 3. Целевая структура
```
app/
  domains/
    competitors/
      facade.py            # публичные методы для API и фоновых задач
      dto.py               # DTO/схемы (snapshots, change events)
      repositories/
        competitor_repo.py
        pricing_repo.py
        change_event_repo.py
      services/
        ingestion.py       # сбор данных (scrapers/adapters)
        diffing.py         # сравнение снимков, вычисление изменений
        notifications.py   # подготовка payload к уведомлениям
      scrapers/
        adapters.py        # интерфейсы к внешним провайдерам (reuse с news?)
      tasks.py             # интеграция с Celery (seed, re-scan, digest)
```
- **Facade**: единая точка для API (`list_competitors`, `get_change_log`, `rescan_pricing`, `generate_digest`).  
- **Services**: разбитые по обязанностям (ingestion, diffing, notifications).  
- **Repositories**: строгий доступ к ORM моделям (Competitor, PricingSnapshot, ChangeEvent).  
- **Tasks**: Celery вызывает фасад и сервисы, не напрямую ORM.

## 4. План миграции
1. **Подготовка инфраструктуры (B-204-1)**  
   - Создать пакет `app/domains/competitors` со scaffolding.  
   - Перенести модели импортов (facade → repositories → services).  
   - Определить `CompetitorFacade` интерфейс.

2. **Репозитории (B-204-2)**  
   - Вынести ORM запросы из `competitor_service.py` в репозитории (`fetch_by_slug`, `list_snapshots`, `get_latest_change`).  
   - Обеспечить unit-тесты на SQLite (аналогично news).

3. **Сервисы (B-204-3)**  
  - ✅ `CompetitorIngestionDomainService` (ingest + diff + snapshot через доменные репозитории).  
  - ✅ `CompetitorChangeDomainService` + репозитории (`PricingSnapshotRepository`, `ChangeEventRepository`); diff/summary логика перенесена в домен (`services/diff_engine.py`).  
  - ✅ NotificationService (payload → NotificationDispatcher).
- 2025-11-10: создан `CompetitorRepository` (fetch/list/get/delete/save, upsert компании) и фасад `CompetitorFacade`, API переведено на фасад при сохранении legacy логики.  
- 2025-11-10: добавлен `CompetitorChangeDomainService` — адаптер над legacy `CompetitorChangeService` для постепенной миграции.  
- 2025-11-10: создан `CompetitorIngestionDomainService`, фасад предоставляет единый доступ к ingestion/diff.
- 2025-11-10: создан пакет `app/tasks/competitors.py` и доменные адаптеры `app/domains/competitors/tasks.py` для Celery (ingest pricing, recompute/list change events).
- 2025-11-10: diff/summary логика перенесена в доменные сервисы (`diff_engine`, обновлён `CompetitorChangeDomainService`), legacy `CompetitorChangeService` стал тонкой обёрткой.  
- 2025-11-11: добавлен `CompetitorNotificationService` — выбирает подписчиков (`UserPreferences` + `NotificationSettings`), формирует payload и вызывает `NotificationDispatcher` с дедупликацией, статус `notification_status` обновляется на `sent/ skipped`.  
- 2025-11-11: `CompetitorIngestionDomainService` вызывает уведомления автоматически, фасад получил метод `notify_change_event`, добавлены unit-тесты `tests/unit/domains/competitors/test_notification_service.py`.

4. **Facade и API (B-204-4)** ✅  
   - Создан `CompetitorFacade`, dependency `get_competitor_facade` обновлён.  
   - `app/api/v1/endpoints/competitors.py` и связанные ручки переведены на фасад (ingest/list/recompute).  
   - DTO и сериализация согласованы с новыми сервисами.

5. **Celery интеграция (B-204-5)** ✅  
   - Доменные адаптеры `app/domains/competitors/tasks.py` и модуль `app/tasks/competitors.py` вызывают фасад.  
   - Задачи pricing ingestion и recompute интегрированы в `celery_app`.  
   - Legacy задачи-обёртки обновлены; еager-тесты покрывают happy-path.

6. **Документация и тесты (B-204-6)** ✅  
   - Добавлены unit-тесты для сервисов/репозиториев (`tests/unit/domains/competitors/*`).  
   - Интеграционные тесты API `/api/v1/competitors/changes` и export сценарии обновлены.  
   - Обновлены `phase2_bounded_contexts.md`, README, backlog (`B-204` закрыт).

## 5. Влияние
- **API**: изменения dependency injection, ресериализация.  
- **Celery**: задачи будут вызывать фасад; возможно обновление расписаний.  
- **Уведомления**: требуется убедиться, что `NotificationDispatcher` получает те же события (см. Phase 3).  
- **Фронтенд**: контракты должны остаться неизменными — необходимо зафиксировать OpenAPI перед миграцией.

## 6. Риски и меры
- **Риск регрессов change log:** зафиксировать baseline (существующие события) и проверить после миграции.  
- **Scraper зависимости:** уточнить совместимость с планом B-203 (адаптеры скраперов).  
- **Синхронизация с analytics:** удостовериться, что аналитика не зависит напрямую от старого сервиса (иначе добавить адаптер).

## 7. Статус
- **Статус:** ✅ Завершено (11 Nov 2025).  
- **Follow-up:** e2e Celery сценарии и мониторинг вынесены в `B-302` (idempotency/observability); фронтовые подписки — в Wave 3 UI задач.

---

**Подпись:** GPT-5 Codex — 10 Nov 2025

