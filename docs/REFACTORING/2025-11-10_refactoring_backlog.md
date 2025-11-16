# Refactoring Backlog — 10 Nov 2025

> Чек-лист задач, сформированный на основе `2025-11-10_refactoring_master_plan.md`.  
> Нумерация условная (B — backend, F — frontend, X — cross-cutting). Указывайте исполнителей и статусы в трекере (Jira/Linear и т.д.).

---

## Phase 0 — Подготовка (Pre-flight)
- **X-001 · Утвердить владельцев направления**  
  _Owner:_ Engineering Manager  
  _Deliverable:_ список ответственных за backend, frontend, QA, DevOps, обновлённый master-plan с контактами.  
  _Checklist:_  
  1. Определить роли (Backend Lead, Frontend Lead, QA Lead, DevOps/Platform).  
  2. Согласовать персоналии и доступность на ближайшие 2–3 фазы.  
  3. Добавить блок “Owners & Contacts” в `2025-11-10_refactoring_master_plan.md`.  
  4. Расшарить список в общем канале (Slack/Teams) и зафиксировать в трекере.
- **X-002 · Снять baseline метрики**  
  _Owner:_ DevOps  
  _Details:_ latency ключевых API (`/api/v1/news`, `/api/v2/analytics/...`), Celery throughput, веб-виталисты (LCP/FID/CLS) через Lighthouse/Playwright trace. Зафиксировать в Confluence/Notion.  
  _Checklist:_  
  1. Использовать шаблон `phase0_baseline_metrics.md` (API, Celery, Frontend разделы).  
  2. Прогнать `ab`/`hey` или k6 короткие тесты для API, зафиксировать P95/P99 и расход ресурсов.  
  3. Снять Celery метрики: среднее время задачи, количество задач/час, доля ошибок.  
  4. Провести Lighthouse (mobile + desktop) и Playwright trace для ключевых сценариев.  
  5. Заполненный шаблон сохранить в `docs/REFACTORING/metrics/` и дать ссылку команде.
_Progress:_  
- Подготовлена инструкция `docs/REFACTORING/metrics/2025-11-12_baseline.md` (нагрузочные сценарии, команды для Prometheus/Lighthouse).  
- Метрики Celery собираются автоматически (см. `B-302`). Следующий шаг — выполнить нагрузочные замеры и заполнить шаблон.
- **X-003 · Проверка alembic history на staging**  
  _Owner:_ Backend  
  _Details:_ прогон `poetry run alembic upgrade head` на копии базы, сверка ревизий, фиксация checklist’а.  
  _Checklist:_  
  1. Создать fresh БД (локально/staging) и накатить текущий `init.sql` при необходимости.  
  2. Выполнить `poetry run alembic upgrade head` из `backend/`, убедиться в успешном завершении.  
  3. Сверить `alembic history --verbose` с рабочим окружением (Railway/Prod).  
  4. Зафиксировать результаты в `db/phase0_alembic_checklist.md` (дата, окружение, ревизии, заметки).  
  5. Обновить main README (раздел “Миграции”), если обнаружены расхождения или требуются дополнительные шаги.
- **X-004 · Обновление документации окружений**  
  _Owner:_ DevOps + Backend  
  _Details:_ синхронизировать `.env`, `docker-compose.yml`, Railway/Render конфиги; обновить разделы README/SETUP.  
  _Checklist:_  
  1. Сверить переменные окружения между `env.example`, `env.production`, Railway/Render dashboards.  
  2. Обновить `SETUP.md` и `README.md` (разделы с окружениями и запуском), указать актуальные переменные и команды.  
  3. Проверить `docker-compose.yml` на соответствие актуальным сервисам (postgres/redis/worker), описать особенности запуска.  
  4. Задокументировать отличия продакшен/стейджинг окружений (порт, hostname, feature flags).  
  5. Сохранить заметки в `docs/REFACTORING/environment/phase0_env_sync.md` + при необходимости приложить diff.

## Phase 1 — Stabilisation
- **B-101 · Включить автоматический запуск миграций** ✅  
  _Owner:_ Backend  
  _Tasks:_ переработать `backend/main.py.apply_migrations` (логика попытки + fallback + логирование), покрыть smoke-тестом. Добавить флаг `RUN_MIGRATIONS` в конфиги и документацию.  
  _Progress:_ `apply_migrations` обновлён, флаг `RUN_MIGRATIONS` добавлен в `backend/env.*`, README и чек-листы.
- **B-102 · OpenAPI snapshot & проверка в CI** ✅  
  _Owner:_ Backend  
  _Tasks:_ генерировать `openapi.json`, добавить проверку на изменения в CI (fail без review). Использовать скрипт `poetry run python scripts/generate_openapi.py`.
  _Progress:_  
  - `openapi.json` хранится в корне репозитория, генерация проходит через `backend/scripts/generate_openapi.py` (скрипт допилен: настройка `PYTHONPATH`, защита от pool-параметров SQLite, установка дефолтных env).  
  - В CI (`.github/workflows/ci.yml`) добавлен шаг, который регенерирует схему и падает при расхождении.  
  - `aiosqlite` добавлен в зависимости backend, чтобы генерация работала из изолированных окружений/CI.
- **F-101 · Playwright baseline сценарии**  
  _Owner:_ Frontend QA  
  _Flows:_ Competitor Analysis → Export, Digest Settings, Notifications. Сохранить скриншоты/видео для сравнения.  
  _Checklist:_  
  1. Заполнить шаблон `tests/phase0_playwright_baseline.md` (состояние окружения, версии браузеров, сценарии).  
  2. Выполнить `npm run test:e2e -- --grep "Baseline"` (или отдельные spec’и), приложить отчёт/скриншоты.  
  3. Сохранить trace/video в общий артефакт (например, `frontend/playwright-report/baseline/`).  
  4. Зафиксировать выявленные проблемы/замедления, добавить ссылки на тикеты.  
  5. Поделиться итогом в QA-канале и обновить backlog статус задачи.
- **X-101 · Каталог API вызовов**  
  _Owner:_ Backend + Frontend  
  _Details:_ карта “endpoint ↔ клиентский вызов” (начиная с `ApiService`) для контроля контракта.  
  _Checklist:_  
  1. Использовать шаблон `api/phase1_endpoint_catalog.md`.  
  2. Проиндексировать основные REST и WebSocket ручки (v1, v2) и указать соответствующие места в `frontend/src/services`.  
  3. Отметить требуемые scopes/авторизацию, типы ответов и наличие интеграционных тестов.  
  4. Добавить ссылку на openapi.json, если endpoint ещё не документирован.  
  5. Согласовать документ с командами backend/frontend и обновить backlog статус.

## Phase 2 — Domain Decomposition
- **B-201 · Проектирование bounded contexts** 🔄  
  _Owner:_ Backend  
  _Tasks:_ RFC по отдельным модулям (News, Analytics, Notifications, Competitor Intelligence), список сервисов/файлов для переноса. Базовый план — `backend/phase2_bounded_contexts.md` (обновлять по мере утверждения).  
_Progress:_  
- Waves 1–2 закрыты; документ обновлён ссылками на план волны (`backend/phase2_bounded_contexts.md`).  
- Wave 3 (Analytics) — фасад и snapshot/comparison сервисы перенесены в `app/domains/analytics`, API v2 и Celery используют фасад; план `backend/phase2_analytics_wave3_plan.md` актуализирован (осталось вынести экспорт/репозитории).  
- Wave 4 (Notifications & Digests) — добавлен фасад `app/domains/notifications/NotificationsFacade`, обновлены API и Celery таски; следующая итерация — миграция dispatcher/digest сервисов в домен (см. `backend/phase2_notifications_wave4_plan.md`).
- Wave 5 (Shared/Auth) — план `backend/phase2_shared_services_wave5_plan.md`, фокус на users, feature flags, shared security.  
- Следующий шаг — завести подзадачи в трекере (B-201-3a…c, B-201-4a… и т.д.), синхронизировать сроки с frontend roadmap.
- **B-202 · Инкапсуляция raw SQL** ✅  
  _Owner:_ Backend  
  _Details:_ инвентаризировать endpoints с SQL строками (`users.py`, `notifications.py` и т.д.), определить порядок переписывания на SQLAlchemy Core. Итоги инвентаризации — `backend/phase2_raw_sql_inventory.md`.  
  _Progress:_  
  - Утилита `scripts/simple_fix_categories.py` переписана на SQLAlchemy AsyncSession (без прямых `SELECT/UPDATE`).  
  - Добавлен guard `scripts/check_no_raw_sql.py`, выполняется в CI и предотвращает появление сырых запросов в `app/`.  
  - Инвентаризация обновлена, runtime код не содержит raw SQL.
- **B-203 · Scraper interface extraction** ✅  
  _Owner:_ Backend  
  _Tasks:_ выделить интерфейсы для `UniversalBlogScraper`, Playwright fallback, конфигурации источников. План — `backend/phase2_scraper_interface_plan.md` (B-203-1…5).  
  _Progress:_ интерфейсы/адаптеры/реестр внедрены, Celery и CLI/скрипты используют `NewsScraperService`, API `companies.scan_company` использует реестр; unit/integration тесты добавлены.
- **B-204 · Competitor Intelligence реорганизация** ✅  
  _Owner:_ Backend  
  _Tasks:_ выделить доменный пакет `competitors`, перенести ingestion/diff/notifications в фасад, обновить Celery и API. План — `backend/phase2_competitor_refactor_plan.md`.  
_Progress:_  
- `CompetitorFacade` / `CompetitorRepository` (включая upsert компаний) / `CompetitorChangeDomainService` / `CompetitorIngestionDomainService` подключены, API работает через фасад.  
- Celery слой переведён на фасад: добавлены `app/domains/competitors/tasks.py` + `app/tasks/competitors.py`, включены в `celery_app`.  
- diff/summary логика перенесена в домен (`services/diff_engine.py`, обновлён `CompetitorChangeDomainService`), legacy сервис остался тонкой обёрткой.  
- Тесты: `tests/unit/domains/competitors/test_tasks.py` и `tests/integration/api/test_competitor_change_endpoints.py` покрывают ingest/list/recompute; уведомления проверены unit-тестами.  
- Добавлен `CompetitorNotificationService` (`backend/app/domains/competitors/services/notification_service.py`): подбор подписчиков, постановка событий в `NotificationDispatcher`, обновление `notification_status`. Фасад получил метод `notify_change_event`, ingest вызывает уведомления автоматически.  
- Follow-up: вынос e2e Celery сценариев и фронтовых контролов подписок перенесён в backlog `B-302` / фронтовые задачи.
- **F-201 · Декомпозиция CompetitorAnalysisPage**  
  _Owner:_ Frontend  
  _Steps:_ дизайн будущих подпакетов (filters, analytics board, change log, export), план миграции состояния/хуков.
- **F-202 · Введение TanStack Query**  
  _Owner:_ Frontend  
  _Details:_ определить запросы первой волны (analytics comparison, change events, report presets), подготовить общие конфиги клиента.
- **F-203 · Типизация shared utilities**  
  _Owner:_ Frontend  
  _Tasks:_ создать модуль форматтеров (дат, валют, приоритетов), покрыть типами и тестами.

## Phase 3 — Quality & Performance
- **B-301 · Интеграционные тесты аналитики** ✅  
  _Owner:_ Backend QA  
  _Scope:_ `analytics_comparison_service`, `company_analytics_snapshots`, Celery задачи на recompute/export.
_Progress:_  
- Сформирован план `docs/REFACTORING/tests/phase3_analytics_testing_plan.md`.  
- Добавлены baseline тесты: `tests/unit/services/test_analytics_service.py`, `tests/unit/services/test_analytics_comparison_service.py`, `tests/integration/api/test_analytics_endpoints.py`, `tests/integration/tasks/test_analytics_tasks.py`, `tests/integration/api/test_analytics_comparison_endpoints.py`.  
- Расширены data builders (`tests/utils/analytics_builders.py`) для graph edges, notification presets, export сценариев.  
- Тесты встроены в CI (`pytest -m "not e2e"`), результаты зелёные. Дополнительные multi-subject сценарии заведены отдельными тикетами (опционально).
- **B-302 · Idempotency & observability Celery**  
  _Owner:_ Backend  
  _Tasks:_ внедрить метрики (Prometheus/OpenTelemetry), добавить guard’ы от повторных обработок.
_Progress:_  
- Prometheus/OTel экспортёр добавлен (`app/instrumentation/celery_metrics.py`), метрики доступны по `http://localhost:9464/metrics`.  
- Дедупликация аналитических задач реализована (ключи `analytics:<scope>:...`, unit-тесты `tests/unit/tasks/test_analytics_task_guards.py`).  
- Следующий шаг: собрать фактические метрики в `docs/REFACTORING/metrics/phase0_baseline_metrics.md`, добавить алерты/дашборды.
- **F-301 · Vitest покрытие hooks/services**  
  _Owner:_ Frontend  
  _Targets:_ новые hooks анализа, `ApiService` утилиты, форматтеры.
- **F-302 · Playwright e2e расширение**  
  _Owner:_ Frontend QA  
  _Flows:_ ручное добавление конкурента, подписки/уведомления, edge-cases analytics (404 → empty state).
- **X-301 · Автоматизация код-стандарта**  
  _Owner:_ DevOps  
  _Tasks:_ Makefile/Taskfile (`make lint`, `make test`, `make e2e`), pre-commit с ruff/eslint/vitest.

## Phase 4 — Extensibility & Vision
- **B-401 · Feature flag framework**  
  _Owner:_ Backend  
  _Options:_ FastAPI middleware + storage (Postgres/Redis), CLI для переключения.
- **B-402 · Shared schema generation**  
  _Owner:_ Backend + Frontend  
  _Tasks:_ генерация TypeScript типов из OpenAPI (например, `openapi-typescript`), интеграция в build.
- **F-401 · Дизайн-токены/темизация**  
  _Owner:_ Frontend  
  _Details:_ Tailwind config → дизайн-токены, документация по использованию.
- **X-401 · Roadmap по новым направлениям**  
  _Owner:_ Product + Data Science  
  _Output:_ документ развития (LLM-инсайты, BI интеграции, коллаборативные фичи), согласованный с мастер-планом.

---

### Дополнительные заметки
- Каждая задача должна иметь критерии приемки (DoD) и связь с мастер-планом.
- Рекомендуемая конфигурация статусов: _planned_ → _in progress_ → _review_ → _done_.
- Обновляйте этот файл при каждой смене фаз или крупном изменении состава задач.

Prepared by: GPT-5 Codex — 10 Nov 2025

