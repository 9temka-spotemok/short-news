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

### 3.2 Competitor Intelligence — 🔄 в прогрессе
- **Готово:** `app/domains/competitors/facade.py`, репозитории (`competitor`, `pricing_snapshot`, `change_event`), базовые сервисы (`ingestion_service`, `change_service`), API `competitors.py` и CLI (`seed_competitors.py`, скрипты импорта) переподключены. Добавлены доменные адаптеры и Celery задачи (`app/domains/competitors/tasks.py`, `app/tasks/competitors.py`) для ingestion и recompute.
- **В очереди:** вынести diff/ingestion пайплайн в домен (парсеры, планировщик Celery), формализовать адаптеры уведомлений. Детализация — `phase2_competitor_refactor_plan.md`, `phase2_competitor_ingestion_plan.md`.
- **Тесты:** unit/integration сценарии готовятся (`tests/unit/domains/competitors/test_tasks.py`, `tests/integration/api/test_competitor_change_endpoints.py`), впереди — CLI/ Celery eager.

### 3.3 Analytics & Reports — 🟡 планирование
- **Текущее состояние:** монолитные сервисы (`analytics_service`, `analytics_comparison_service`) сочетают пересчёт, агрегацию, экспорт.
- **Планируемая структура:**
  - `domains/analytics/facade.py` — единая точка доступа.  
  - `services/snapshot_service.py` — агрегация и чтение метрик.  
  - `pipelines/recompute_runner.py` — запуск Celery задач и управление зависимостями.  
  - `exporters/report_builder.py` — генерация JSON/PDF/CSV.  
  - `repositories/analytics_repository.py` (план) — доступ к таблицам snapshots/graph.
- **Key TODO:** выделить DTO для `/api/v2/analytics/*`, сформировать план тестирования (Phase3 B-301).

### 3.4 Notifications & Digests — 🟡 планирование
- **Текущее состояние:** логика рассредоточена по `notification_dispatcher`, `notification_delivery_executor`, `digest_service`, `app/tasks/notifications.py`, `app/tasks/digest.py`.
- **Планируемая структура:**
  - `domains/notifications/facade.py` — orchestration user preferences + каналы.  
  - `services/dispatcher.py` — маршрутизация событий и построение доставок.  
  - `senders/*` — конкретные каналы (telegram/email/webhook).  
  - `templates/digest_renderer.py` — генерация дайджеста (общая для email/telegram).  
  - `repositories/*` — хранение подписок, событий, попыток.  
- **Key TODO:** определить границы с Competitor/Analytics (кто публикует события), добавить контрактные тесты.

### 3.5 Auth & Users — ⚪️ поддержание
- Сохраняем в `app/domains/users` (план на Phase 3) — минимальный приоритет, т.к. текущее разделение терпимо.

## 4. Итерационный план (waves)
| Wave | Фокус | Deliverables | Зависимости |
|------|-------|--------------|-------------|
| **Wave 1 (Done)** | News & Scraping | Фасад, репозитории, сервисы, скраперы, тесты | Завершено (B-201-1, B-203) |
| **Wave 2 (In flight)** | Competitor Intelligence | Фасад, ingestion/change сервисы, перевод API/CLI | На стыке с B-204, ожидается завершение Celery миграции |
| **Wave 3 (Planned)** | Analytics | Архитектура pipelines/exporters, выделение фасада, DTO | Требует устоявшегося OpenAPI (B-102) и базы метрик |
| **Wave 4 (Planned)** | Notifications & Digests | Dispatcher, senders, шаблоны, интеграция с analytics events | Нужен план событий от Analytics/Competitor |
| **Wave 5 (Planned)** | Общие сервисы | Auth/Users домен, shared infrastructure пакеты | После стабилизации основных контекстов |

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

