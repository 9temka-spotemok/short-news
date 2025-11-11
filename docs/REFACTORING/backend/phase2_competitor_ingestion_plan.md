# Phase 2 — Competitor Ingestion & Diff Plan (B-204)

Дата: 2025-11-10  
Подготовил: GPT-5 Codex

---

## 1. Цель
- Перенести ingestion/diff логики конкурентного модуля в новый доменный пакет `app/domains/competitors`.
- Стандартизировать работу Celery задач, парсеров и фасада с учётом новых сервисов (`CompetitorIngestionDomainService`, `CompetitorChangeDomainService`).
- Упростить тестирование и интеграцию с уведомлениями/аналитикой.

## 2. Текущее состояние
- `competitor_change_service.py` выполняет:
  - Парсинг HTML (PricingPageParser).
  - Сохранение `CompetitorPricingSnapshot`.
  - Расчёт diff и создание `CompetitorChangeEvent`.
- `seed_competitors.py` и другие операции работают напрямую с ORM и legacy сервисами.
- Celery задачи (notifications, scraping) опираются на legacy сервисы без фасада.

## 3. Целевая архитектура
```
app/
  domains/
    competitors/
      services/
        ingestion_service.py   # инкапсулирует ingest_pricing_page
        diff_service.py        # вычисляет diff из snapshot данных
        notification_service.py# подготовка уведомлений (B-204-5)
      repositories/
        pricing_snapshot_repo.py
        change_event_repo.py
        company_repo.py
      facade.py                # уже создан; оркестрирует ingestion/diff/notifications
      tasks.py                 # Celery обёртки (scrape_pricing, recompute, notify)
```

## 4. План миграции (B-204-2 … B-204-6)
1. **B-204-2: Репозитории**
   - Вынести операции по работе с `CompetitorPricingSnapshot`, `CompetitorChangeEvent`, `Company` в отдельные репозитории.
   - Обновить `CompetitorChangeDomainService` для использования репозиториев (временно допускается legacy вызов).

2. **B-204-3: Сервисы**
   - `CompetitorIngestionDomainService.ingest_pricing_page` → парсинг, сохранение snapshot, вызов diff.
   - `CompetitorChangeDomainService` → чистый diff, статус, подготовка payload.
   - Подготовить `CompetitorNotificationDomainService` (получение событий + подготовка сообщений).

3. **B-204-4: Обновление фасада**
   - Расширить `CompetitorFacade` методами `ingest_pricing`, `get_change_events`, `trigger_notifications`.
   - Обновить API, фоновые задачи, CLI на фасадные вызовы.

4. **B-204-5: Celery интеграция**
   - Перевести `seed_competitors.py`, `notifications.py`, `scraping.py` (competitor раздел) на новый фасад.
   - Добавить новые Celery задачи (сканинг pricing, recompute diff).

5. **B-204-6: Тесты и документация**
   - Unit тесты для новых сервисов/репозиториев.
   - Интеграционные тесты API `/api/v1/competitors/changes`, `/recompute`.
   - Обновить README, `phase2_bounded_contexts.md`, backlog, планы.

## 5. Промежуточный статус
| Компонент | Что сделано | Что осталось |
|-----------|-------------|--------------|
| `CompetitorFacade` | ✅ Создан, API подключено, ingestion/diff сервисы доступны | Добавить методы уведомлений |
| `CompetitorRepository` | ✅ fetch/list/get/delete/save + upsert компании | Вынести командные операции (bulk) |
| `PricingSnapshotRepository` / `ChangeEventRepository` | ✅ Созданы, интегрированы в domain сервисы | Расширить вспомогательными методами (bulk/history) |
| `CompetitorChangeDomainService` | ✅ Использует новые репозитории, обёртка legacy diff | Полностью заменить содержание на доменную реализацию |
| `CompetitorIngestionDomainService` | ✅ Инкапсулирует парсинг, snapshot и diff через репозитории | Добавить NotificationService/расширение |
| Celery | Создан `app/domains/competitors/tasks.py`, добавлен модуль `app/tasks/competitors.py` (ingest pricing, recompute/list change events) | Завершить миграцию legacy задач и покрытия тестами |
| Diff engine | Выделен `services/diff_engine.py`, `CompetitorChangeDomainService` и ingestion используют новую логику; legacy сервис — thin wrapper | Связать с уведомлениями и аналитикой, удалить остатки после внедрения |
| Тесты | Добавлены unit-тесты `tests/unit/domains/competitors/test_tasks.py` и интеграционные `tests/integration/api/test_competitor_change_endpoints.py` | Дополнить проверками CLI/Celery eager |

## 6. Риски
- **Парсеры**: PricingPageParser тесно связан с HTML и snapshot хранением → требуется аккуратный рефактор.
- **Уведомления**: зависят от change events, необходимо удостовериться в совместимости.
- **Тесты**: legacy код не покрыт тестами → необходимы smoke-tests после миграции.

## 7. Следующие шаги
1. Реализовать репозитории pricing/change events.
2. Перенести `CompetitorChangeService` логику внутрь доменных сервисов.
3. Обновить Celery/API и добавить тесты.
4. Финализировать документацию и закрыть B-204.

---

**Статус:** в работе (10 Nov 2025)  
**Подпись:** GPT-5 Codex

