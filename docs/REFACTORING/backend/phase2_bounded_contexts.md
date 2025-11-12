# Phase 2 — Backend Bounded Context Plan

Дата: 2025-11-10  
Подготовил: GPT-5 Codex (Senior Dev mode)

---

## 1. Цели
- Развести доменную логику по контекстам, чтобы снизить связность и облегчить рефакторинг.
- Обеспечить явные интерфейсы между контекстами (структура зависимостей, DTO/схемы).
- Подготовить почву для дальнейшего тестового покрытия и оптимизации производительности.

## 2. Текущее состояние (высокоуровневый обзор)

| Контекст | Основные модули | Осн. модели | Ключевые API/сервисы | Наблюдения |
|----------|-----------------|-------------|----------------------|------------|
| **News & Scraping** | `app/services/news_service.py`, `app/tasks/scraping.py`, `app/scrapers/*` | `NewsItem`, `NewsKeyword`, `ScraperState` | `/api/v1/news/*`, cron Celery | Логика разбросана между API, сервисами и скриптами; нет единой точки для бизнес-правил. |
| **Competitor Intelligence** | `app/services/competitor_service.py`, `competitor_change_service.py` | `CompetitorChangeEvent`, `CompetitorPricingSnapshot` | `/api/v1/competitors/*`, `/api/v1/companies/scan` | Сервис конкурентов смешивает CRUD, сканирование и аналитические операции. |
| **Analytics & Reports** | `app/services/analytics_service.py`, `analytics_comparison_service.py`, `app/tasks/analytics.py` | `CompanyAnalyticsSnapshot`, `ImpactComponent`, `AnalyticsGraphEdge` | `/api/v2/analytics/*`, Celery `recompute_all_analytics` | Внутренние структуры сложные, но API v2 уже выделен; нужно разделить расчёт, сериализацию, экспорты. |
| **Notifications & Digests** | `app/services/notification_*`, `digest_service.py`, `app/tasks/notifications.py`, `app/tasks/digest.py` | `Notification`, `NotificationEvent`, `UserPreferences` | `/api/v1/notifications/*`, Telegram | Смешаны каналы доставки, настройки, генерация дайджестов. |
| **Auth & Users** | `app/api/v1/endpoints/auth.py`, `users.py`, `app/services/telegram_service.py` | `User`, `UserPreferences` | `/api/v1/auth/*`, `/api/v1/users/*`, Telegram webhook | В основном стабильно, но есть raw SQL и специфичная логика Telegram. |


## 3. Целевая структура и статусы по контекстам

```
app/
  domains/
    news/
      facade.py
      services/
        ingestion_service.py
        query_service.py
        scraper_service.py
      repositories/
        news_repository.py
        company_repository.py
      dtos/
        stats.py
      scrapers/
        interfaces.py
        adapters.py
        registry.py
      tasks.py
    competitors/
      facade.py
      services/
        ingestion_service.py
        change_service.py
      repositories/
        competitor_repository.py
        pricing_snapshot_repository.py
        change_event_repository.py
      adapters/
        parsing.py (план)
        notifications.py (план)
    analytics/
      facade.py (план)
      services/
        snapshot_service.py (план)
        knowledge_graph_service.py (план)
      pipelines/
        recompute_runner.py (план)
        batch_jobs.py (план)
      exporters/
        report_builder.py (план)
    notifications/
      facade.py (план)
      services/
        dispatcher.py (план)
        preferences_service.py (план)
      senders/
        telegram.py (план)
        email.py (план)
        webhook.py (план)
      templates/
        digest_renderer.py (план)
  api/
    v1/
    v2/
  infrastructure/
    db/
    celery/
    external/
```

- **domains/** — бизнес-ядро с фасадами, сервисами, репозиториями и DTO.
- **infrastructure/** — адаптеры ко внешним системам (БД, Celery, HTTP, провайдеры AI).
- API-слой работает только через фасады доменов.

### 3.1 News & Scraping — ✅ стабилизирован
- **Файлы:** `app/domains/news/*` (facade, services, repositories, scrapers, DTO, Celery-адаптеры).
- **API/Celery:** `/api/v1/news/*`, `app/tasks/scraping.py`, `app/tasks/nlp.py` используют фасад.
- **Тесты:** `tests/unit/domains/news/*`, `tests/integration/api/test_news_endpoints.py`, `tests/integration/tasks/test_scraping_task.py`, `test_nlp_tasks.py`.
- **Следующие шаги:** завершить перенос NLP провайдера и переиспользовать registry для CLI (см. `phase2_news_refactor_plan.md`).

### 3.2 Competitor Intelligence — ✅ стабилизирован
- **Готово:** `app/domains/competitors/facade.py`, репозитории (`competitor`, `pricing_snapshot`, `change_event`), сервисы (`ingestion_service`, `change_service`, `notification_service`), Celery адаптеры (`app/domains/competitors/tasks.py`, `app/tasks/competitors.py`). API и legacy CLI используют фасад.
- **Тесты:** unit (`tests/unit/domains/competitors/test_tasks.py`, `test_notification_service.py`) и integration (`tests/integration/api/test_competitor_change_endpoints.py`, `test_analytics_comparison_endpoints.py`).
- **Follow-up:** расширенные e2e Celery сценарии и наблюдаемость зафиксированы в `B-302`.

### 3.3 Analytics & Reports — 🔄 в прогрессе (Wave 3)
- **План реализации:** см. `backend/phase2_analytics_wave3_plan.md`.  
- **Фокус:** фасад, репозитории, сервисы snapshot/comparison/export, pipelines для Celery.  
- **Прогресс:** добавлен `app/domains/analytics/` (facade, snapshot/comparison services), API v2 и Celery переведены на фасад, unit/integration тесты обновлены.  
- **Следующие шаги:** реализовать `app/domains/analytics/*`, перевести API v2 и Celery, обновить тесты согласно плану.

### 3.4 Notifications & Digests — 🔄 в прогрессе (Wave 4)
- **План реализации:** см. `backend/phase2_notifications_wave4_plan.md`.  
- **Фокус:** фасад уведомлений, каналы, дайджесты, перенос Celery задач в домен.  
- **Прогресс (12 Nov 2025):** фасад подключён ко всем точкам входа; вынесены репозитории (`channels/events/deliveries/settings/preferences`), `DispatcherService` переписан на доменный слой, `notification_service.py`/`digest_service.py` стали thin adapters.
- **Следующие шаги:** завершить миграцию Celery пайплайнов (`app/tasks/notifications.py`, `app/tasks/digest.py`) на доменные сервисы и сформировать channel/pipeline сервисы.

### 3.5 Shared Services & Auth — 🟡 планирование (Wave 5)
- **План реализации:** см. `backend/phase2_shared_services_wave5_plan.md`.  
- **Фокус:** выделение домена `users`, платформа feature flags, shared security/integrations.  
- **Следующие шаги:** после Wave 3-4 зафиксировать сроки реализации feature flags и shared infrastructure.

## 4. Итерационный план (waves)
| Wave | Фокус | Deliverables | Зависимости |
|------|-------|--------------|-------------|
| **Wave 1 (Done)** | News & Scraping | Фасад, репозитории, сервисы, скраперы, тесты | Завершено (B-201-1, B-203) |
| **Wave 2 (Done)** | Competitor Intelligence | Фасад, ingestion/change/notification сервисы, перевод API/CLI, Celery адаптеры | Завершено (B-204). Follow-up: `B-302` для метрик/idempotency |
| **Wave 3 (In progress)** | Analytics | Фасад, репозитории, сервисы snapshot/comparison/export, pipelines | Требует устоявшегося OpenAPI (B-102) и базы метрик |
| **Wave 4 (In progress)** | Notifications & Digests | Dispatcher, каналы, дайджесты, Celery pipelines | Зависит от событий Competitor/Analytics |
| **Wave 5 (Planned)** | Общие сервисы | Auth/Users домен, shared infrastructure пакеты | После стабилизации Wave 3–4 и запуска feature flags |

## 5. Артефакты и ToDo
- ADR на каждый wave (привязаны к backlog задачам `B-201-*`, `B-204`, `B-301`).  
- Для каждого домена — таблица зависимостей и целевой coverage (unit + integration + contract tests).  
- Добавить в CI `mypy --namespace-packages` после финальной раскладки структур.  
- При переносе сервисов обновлять `docs/REFACTORING/tests/*` и README (файлы/ответственность).

## 6. Риски и контрольные точки
- **Регрессы API:** поддерживаем `openapi.json` (см. B-102) и готовим contract tests перед Wave 3.  
- **Celery задачи:** каждая миграция домена должна проходить через чеклист idempotency/observability (см. B-302).  
- **Циклические зависимости:** запрещаем импорт домена → домен напрямую; используем фасады и DTO.  
- **Командная синхронизация:** перед стартом Wave 3 согласовать с frontend roadmap (зависимости API v2).

---

Следующий шаг: зафиксировать критические подзадачи для Wave 2 (Celery ingestion, notifications adapters) и вынести отдельные карточки в backlog B-201/B-204.

