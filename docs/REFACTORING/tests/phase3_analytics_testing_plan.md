# Phase 3 — Analytics Testing Plan (B-301)

Дата: 2025-11-10  
Подготовил: GPT-5 Codex

---

## 1. Цели
- Зафиксировать стратегию интеграционного/юнит тестирования аналитического стека перед началом Phase 3.
- Обеспечить покрытие критичных сценариев `analytics_service`, `analytics_comparison_service`, Celery-пайплайнов пересчёта.
- Служить чек-листом для задачи `B-301`.

## 2. Области тестирования
| Область | Что проверяем | Тип тестов |
|---------|---------------|------------|
| **`AnalyticsService`** | `compute_snapshot_for_period`, `refresh_company_snapshots`, `sync_knowledge_graph` | unit (SQLite in-memory) |
| **`AnalyticsComparisonService`** | `build_comparison`, агрегация метрик и событий, экспорт payload | unit/ integration |
| **Celery задачи (`app/tasks/analytics.py`)** | `recompute_company_analytics`, `recompute_all_analytics`, `sync_company_knowledge_graph` | integration (Celery eager) |
| **API `/api/v2/analytics/*`** | получение impact snapshots, запуск пересчёта, экспорт | integration (FastAPI TestClient) |

## 3. Инструменты и фикстуры
- `pytest` + `pytest-asyncio`, общие фикстуры из `tests/conftest.py`.
- In-memory SQLite (fixtures уже создают все таблицы через `Base.metadata.create_all`).
- Для Celery — `celery_app.conf.task_always_eager = True` внутри тестов.
- Подготовка данных через ORM (Company, NewsItem, CompetitorChangeEvent, CompanyAnalyticsSnapshot).

## 4. План тестов
### 4.1 Unit tests
- `tests/unit/services/test_analytics_service.py`
  - `compute_snapshot_for_period` создаёт snapshot и компоненты на основе новостей и change events.
  - `refresh_company_snapshots` — пересчёт нескольких периодов.
- `tests/unit/services/test_analytics_comparison_service.py`
  - Мокаем зависимые сервисы и проверяем агрегацию (`build_comparison`, export payload).

### 4.2 Integration tests
- `tests/integration/api/test_analytics_endpoints.py`
  - `/api/v2/analytics/companies/{company_id}/impact/latest`
  - `/api/v2/analytics/companies/{company_id}/recompute`
- `tests/integration/api/test_analytics_comparison_endpoints.py`
  - `/api/v2/analytics/comparisons` — full-stack агрегация (news, change log, graph)
  - `/api/v2/analytics/export` — export payload + notification/preset контекст
- `tests/integration/tasks/test_analytics_tasks.py`
  - Celery задачи `recompute_company_analytics`, `sync_company_knowledge_graph` в eager режиме.

### 4.3 Smoke / contract checks
- Сверить, что `openapi.json` содержит актуальные описания v2-эндпоинтов.
- При необходимости добавить snapshot сравнение с baseline (опционально).

## 5. Checklist `B-301`
1. [x] Сформировать тестовые data builders для компаний, новостей, change events (`tests/utils/analytics_builders.py`).
2. [x] Написать unit-тесты `AnalyticsService`.
3. [x] Добавить unit/integration-тесты `AnalyticsComparisonService`.
4. [x] Добавить интеграционные тесты API `/api/v2/analytics/*`.
5. [x] Покрыть Celery аналитику (eager).
6. [x] Обновить CI (добавить запуск новых тестов).
7. [x] Обновить документацию и README (раздел “Тестирование” и backlog).

## 6. Риски
- Сложность создания реалистичных данных для diff/компонент → предлагается использовать data builders.
- Celery задачи затрагивают несколько сервисов → важно ограничить eager режимом и моками внешних зависимостей.
- Потенциальное увеличение времени прогона тестов — стоит сгруппировать/маркировать аналитические тесты.

---

**Ответственный:** Backend QA / Engineers  
**Статус:** ✅ Completed (11 Nov 2025) — regression scenarios заведены в backlog отдельно  


