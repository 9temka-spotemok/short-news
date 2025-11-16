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
| `CompetitorFacade` | ✅ Создан, API подключено, ingestion/diff/notifications доступны | — |
| `CompetitorRepository` | ✅ fetch/list/get/delete/save + upsert компаний | Follow-up: bulk операции (перенесено в B-302) |
| `PricingSnapshotRepository` / `ChangeEventRepository` | ✅ Созданы, интегрированы в domain сервисы | Follow-up: history helpers (при необходимости) |
| `CompetitorChangeDomainService` | ✅ Использует новые репозитории и `diff_engine` | — |
| `CompetitorIngestionDomainService` | ✅ Инкапсулирует парсинг, snapshot, diff и уведомления | — |
| Celery | ✅ `app/domains/competitors/tasks.py` + `app/tasks/competitors.py`, интеграция в `celery_app` | Follow-up: расширенные eager/e2e сценарии (B-302) |
| Diff engine | ✅ `services/diff_engine.py` используется ingestion/change сервисами; legacy обёртка сохранена для обратной совместимости | — |
| Тесты | ✅ Unit + integration для задач и API; экспорт сценарии обновлены | Follow-up: CLI/e2e smoke (B-302) |

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

**Статус:** ✅ завершено (11 Nov 2025) — дальнейшие улучшения учтены в задачах `B-302` и фронтовом backlog  
**Подпись:** GPT-5 Codex

