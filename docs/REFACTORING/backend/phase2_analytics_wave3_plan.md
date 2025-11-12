# Phase 2 — Wave 3 Analytics Domain Plan (B-201-Analytics)

**Дата:** 2025-11-12  
**Подготовил:** GPT-5 Codex  
**Статус:** Draft → Ready for execution

---

## 1. Цель волны

Выделить домен `analytics` с явными фасадами, сервисами и репозиториями, чтобы:
- разделить пересчёт снапшотов, агрегирование и экспорт payload’ов;
- сократить связность между API v2 и внутренними сервисами;
- упростить тестирование multi-subject сценариев и экспортов.

## 2. Целевая структура

```
app/domains/analytics/
  __init__.py
  facade.py
  dto.py
  repositories/
    snapshot_repository.py
    impact_component_repository.py
    graph_repository.py
    preset_repository.py
  services/
    snapshot_service.py
    comparison_service.py
    graph_service.py
    export_service.py
  pipelines/
    recompute_runner.py
    knowledge_graph_runner.py
  tasks.py            # Celery адаптеры (wrapper над pipelines)
```

- **facade.py** — публичный API для API v2, Celery и доменных потребителей (notifications, dashboards).
- **dto.py** — сериализуемые структуры для API v2 (`ComparisonResponse`, `ExportPayload`, `NotificationSnapshot`).
- **repositories/** — доступ к `CompanyAnalyticsSnapshot`, `ImpactComponent`, `AnalyticsGraphEdge`, `UserReportPreset`.
- **services/** — бизнес-логика:
  - `snapshot_service`: чтение/агрегация тайм-серий, исторических данных.
  - `comparison_service`: multi-subject сравнения, подготовка breakdown.
  - `graph_service`: построение knowledge graph, связи с notifications.
  - `export_service`: сбор окончательного payload’а, конвертация в форматы.
- **pipelines/** — orchestration Celery задач (деление на этапы, ретраи, chunking).

## 3. Инкрементальный план

| Шаг | Deliverable | Комментарии |
|-----|-------------|-------------|
| 3.1 | Создать пакет `app/domains/analytics` и `facade.py` | Определить интерфейс `get_analytics_facade()` в DI, перенести зависимости из API |
| 3.2 | Репозитории и DTO | Выделить CRUD/queries из `analytics_service.py` и `analytics_comparison_service.py` |
| 3.3 | Сервисы snapshot/comparison/export | Разбить `AnalyticsService` и `AnalyticsComparisonService` на отдельные классы, добавить unit-тесты |
| 3.4 | Pipelines и Celery | Перенести `app/tasks/analytics.py` в домен (`pipelines/`, `tasks.py`), переиспользовать `TaskExecutionContext` |
| 3.5 | API v2 адаптация | Обновить `app/api/v2/endpoints/analytics.py` на фасад, удалить legacy зависимость |
| 3.6 | Тесты и документация | Обновить unit/integration тесты, README, `phase3_analytics_testing_plan.md` |

## 4. Тестовая стратегия

- **Unit:**  
  - `tests/unit/domains/analytics/test_snapshot_service.py`  
  - `tests/unit/domains/analytics/test_comparison_service.py`  
  - `tests/unit/domains/analytics/test_export_service.py`
- **Integration:**  
  - `tests/integration/api/test_analytics_endpoints.py` (обновить фикстуры на фасад)  
  - `tests/integration/tasks/test_analytics_tasks.py` (Celery eager)  
  - Новые сценарии multi-subject → `tests/integration/api/test_analytics_comparison_endpoints.py`
- **Contract:**  
  - Snapshot `openapi.json` (B-102)  
  - Добавить snapshot-тест для экспорт payload’а (сравнение структуры)

## 5. Обновления документации

- `docs/REFACTORING/backend/phase2_bounded_contexts.md` — отметить Wave 3 «In progress».
- README — обновить раздел «Расширенная аналитика и экспорт» (новые файлы).
- `docs/REFACTORING/tests/phase3_analytics_testing_plan.md` — дополнить раздел доменных сервисов.

## 6. Риски и зависиности

- Нужен базовый baseline метрик (Phase 0) для сравнения производительности до/после.
- Возможны изменения API контрактов (`AnalyticsExportResponse`) — согласовать с frontend перед изменением.
- Celery observability (B-302) должен покрывать новые pipelines (ретраи/дедуп ключи).

## 7. Критерии готовности

- API v2 и Celery используют фасад из `app/domains/analytics`.
- Legacy файлы `app/services/analytics_service.py` и `analytics_comparison_service.py` заменены thin-адаптерами или удалены.
- Все существующие тесты проходятся + добавлены новые unit/integration тесты.
- Документация обновлена, backlog B-201-Wave3 отмечен как завершённый.

## 8. Прогресс (12 Nov 2025)

- `app/domains/analytics/` создан: фасад, `SnapshotService`, `ComparisonService` (обёртка над legacy).
- API v2 (`app/api/v2/endpoints/analytics.py`) и Celery задачи (`app/tasks/analytics.py`) переведены на фасад.
- `app/services/analytics_service.py` превращён в совместимый алиас, unit/integration тесты (`tests/unit/services/test_analytics_comparison_service.py`, `tests/integration/api/test_analytics_comparison_endpoints.py`) обновлены.
- Следующий шаг — вынести экспорт/репозитории в домен и заменить legacy `AnalyticsComparisonService` полностью.

