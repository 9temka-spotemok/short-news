# Backend Pre-refactoring Report — 10 Nov 2025

## Scope & Baseline
- **Context:** FastAPI + Celery backend for AI Competitor Insight Hub (`backend/`).
- **Baseline version:** 0.1.0 (per `backend/main.py` and `app/core/config.py`).
- **Artifacts reviewed:** models, services, API routers, Celery tasks, Alembic migrations, configuration, docs. Cross-checked FastAPI dependency patterns via Context7 (`/fastapi/fastapi`).
- **Goal:** Map current architecture, data model, and risk areas to guide refactoring that improves readability, reliability, performance, and scalability without breaking existing behaviour.

## Architecture Overview
- **Entry point:** `backend/main.py` bootstraps FastAPI app, CORS, routers v1/v2, startup hooks.
- **Core layers:**
  - `app/core/` — configuration (`config.py`), database session factory (`database.py`), security, exception handlers.
  - `app/models/` — SQLAlchemy models inheriting from `BaseModel` with timestamp mixin and UUID PKs. Enum types align with Postgres enums.
  - `app/api/` — versioned routers; v1 covers CRUD/auth/news/digest/scheduling/telegram, v2 focuses on analytics.
  - `app/services/` — domain services (news ingestion, analytics computation, notification dispatch, competitor change diffing).
  - `app/tasks/` — Celery task modules orchestrated via `app/celery_app.py`.
  - `app/scrapers/` — scraping toolchain with config registry, heuristics, optional Playwright fallback.
- **Async strategy:** Fully async stack (`asyncpg`, `async_sessionmaker`, `FastAPI` async routes, Celery tasks using async DB sessions when required).
- **Configuration:** Pydantic `Settings` entity with validators for bool flags and JSON host lists. Sensitive defaults enforced (SECRET_KEY required). Feature flags toggle analytics v2 and knowledge graph.
- **Observability:** Loguru used across modules. No centralised tracing/metrics yet.

## Data Layer & Schema
- **Database:** PostgreSQL 16.x with extensive enum usage (`sourcetype`, `newscategory`, analytics enums, notification enums). Alembic migrations stored under `alembic/versions`.
- **Key aggregates:**
  - `users`, `userpreferences`, `notificationsettings`, `notificationchannels` etc for auth/preferences.
  - `news_items`, `news_keywords`, `companyanalyticsnapshots`, `analyticsgraphedges` for news + analytics.
  - `competitor_pricing_snapshots`, `competitor_change_events` for pricing diff pipeline.
  - `crawl_schedules`, `source_profiles`, `crawl_runs` backing dynamic scraping cadence.
  - Activity tracking tables (`useractivities`) supporting engagement metrics.
- **DB helpers:** `BaseModel` offers `to_dict`, `from_dict`, update helpers and auto `__tablename__` fallback (overridden for irregular pluralisation). Timestamp mixin ensures audit fields by default.
- **Schema risks:**
  - **Migrations skipped at runtime:** `main.py.apply_migrations()` is short-circuited (lines 48–75), relying on pre-applied schema. This hides drift and complicates automated deployments.
  - **Enum drift sensitivity:** Hard-coded `create_type=False` for enums assumes types exist; new environments require migration ordering discipline.
  - **Raw SQL usage:** Some endpoints (e.g. `users.py`, `notifications.py`) still craft raw SQL for updates; needs consolidation through SQLAlchemy Core to prevent parameter issues encountered previously.
  - **Search vector management:** `news_items.search_vector` column exists but indexing/population strategy not centralised—ensure triggers or materialisation in place before refactoring.

## API Surface
- **v1 routers:**
  - `auth.py` — JWT issuance (15 min access, 7 day refresh), refresh/ logout endpoints.
  - `news.py` — listing, stats, search (`/news/search`), mark read/favourite actions.
  - `companies.py` — CRUD + `/scan` hooking into scraper overrides.
  - `competitors.py` — change log access & diff recompute.
  - `digest.py`, `notifications.py`, `users.py`, `telegram.py`, `schedules.py`, `admin/scraping.py`.
- **v2 routers:** `analytics.py` — comparisons, impact score snapshots, exports, knowledge graph with feature flag guard.
- **Dependency strategy:** `app/api/dependencies.py` centralises current-user retrieval using `decode_token` + async select (aligns with FastAPI DI guidance). Optional user dependency gracefully handles unauthenticated scenarios.
- **Validation:** Pydantic v2 schemas embedded in models/services; some endpoints rely on manual dict shaping — candidates for schema consolidation.
- **Error handling:** Custom exception setup via `app/core/exceptions`. Response interceptors on frontend expect consistent message fields; ensure we keep compatibility.

## Services & Background Processing
- **Celery:** Configured in `app/celery_app.py` with Redis broker/result backend, dynamic beat schedule pulled from DB (`load_effective_celery_schedule`). Queues: scraping, digest, notifications, analytics.
- **Tasks:** 
  - `tasks.scraping` orchestrates periodic scraping & cleanup.
  - `tasks.nlp` handles classification, sentiment, summarisation (OpenAI-backed).
  - `tasks.digest` generates email/telegram digests with timezone + preference checks.
  - `tasks.notifications` processes event queue, dispatches multi-channel deliveries, cleans old records.
  - `tasks.analytics` recomputes impact metrics, syncs knowledge graph.
- **Services interplay:** 
  - `analytics_service`, `analytics_comparison_service` aggregate metrics, build export payloads (JSON/PDF/CSV).
  - `competitor_change_service` diffing pipeline ensures snapshots/diff mapping.
  - `telegram_service`, `notification_delivery_executor` share sending utilities; reliant on external API keys (SendGrid, Telegram).
  - `scraping_service` glues config registry + heuristics; Playwright fallback toggled by env.
- **Reliability:** Logging with context; need to confirm idempotency for tasks (especially analytics recompute & notification dispatch) ahead of refactor.

## Testing & Tooling
- **Test suites:** Numerous async pytest modules (`test_analytics_v2.py`, `test_digest_settings*.py`, `test_telegram_*`, etc.), but coverage not recently measured. `poetry` config enforces coverage reports and strict markers.
- **CI/CD:** GitHub workflows referenced in root README; ensure new refactors maintain them.
- **Local scripts:** Many helper scripts (`apply_migrations.py`, `debug_database.py`, `quick_db_setup.py`) — plan to rationalise entry points post-refactor.

## Technical Debt & Risk Summary
| Area | Impact | Notes |
| ---- | ------ | ----- |
| Migration bypass | **High** | Runtime skip hides schema drift; ✅ 2025-11-10: `apply_migrations` re-enabled with `RUN_MIGRATIONS` flag and error handling. |
| Configuration sprawl | Medium | ENV parsing in `Settings` is robust, but numerous scripts hardcode `.env`; standardise loader usage. |
| Service coupling | Medium | Analytics/export/diff services tightly coupled (shared response shape). Consider domain boundaries and interface contracts. |
| Task resiliency | Medium | Celery beat dynamic schedule lacks observable audit; add instrumentation + circuit breakers around load failure (currently warnings.warn). |
| Raw SQL remnants | Medium | Past bugfix introduced named parameter rewriting; refactor to ORM/Core patterns to avoid future regressions. |
| Enum maintenance | Medium | Adding new categories/topics requires DB + TS updates; document workflow in README (see action items). |
| Observability | Medium | Loguru present but no structured monitoring/metrics; plan for OpenTelemetry or Prometheus integration. |
| Secrets management | Medium | Settings expects explicit secrets; ensure deployment docs emphasise consistent storage (Railway/Render). |

## Refactoring Opportunities (Mapped to Goals)
- **Readability & Maintainability:** Modularise services around bounded contexts (News, Analytics, Notifications). Introduce explicit interfaces/protocols for service dependencies to simplify testing.
- **Quality & Reliability:** Reinstate migrations in startup, add smoke tests for `/migrations/status`, expand pytest fixtures for analytics diffing. Leverage dependency injection patterns (per Context7 guidance) to share common validation logic across routers.
- **Performance:** Profile analytics recompute + export (consider background caching). Evaluate DB indexes for high-volume tables (`companyanalyticsnapshots`, `competitor_change_events`, `news_items.search_vector`).
- **Developer Velocity:** Consolidate script entry points and provide Makefile/Invoke tasks. Expand typing in services returning dynamic dicts (e.g. analytics payload).
- **Technical Debt Reduction:** Remove legacy duplication in scraper heuristics vs config loader. Migrate raw SQL updates to SQLAlchemy Core. Ensure enumerations defined once (maybe via central metadata).
- **Flexibility & Scalability:** Abstract provider integrations (OpenAI, SendGrid, Telegram) behind adapter interfaces for easy swapping/testing. Use feature flags stored in DB or config service for runtime toggles.
- **Bug Fixing:** Address known issues—e.g. ensure `/companies/scan` override path stable, guard Celery tasks against missing config entries, double-check telemetry for Telegram 409 conflicts.

## Immediate Watchlist Before Major Refactor
1. Reinstate Alembic migrations in startup with safe rollback (detect applied revision, run upgrade head).
2. Capture baseline metrics (DB row counts, Celery throughput, API latency) to compare post-refactor.
3. Inventory environment variables across deployment scripts vs `Settings` defaults; add validation docs.
4. Catalogue external service dependencies (OpenAI, GitHub, Reddit, Twitter, SendGrid, Telegram) and verify mock/ sandbox strategy for testing.
5. Freeze API contract snapshots (OpenAPI) to guard against regressions while refactoring.

## File Responsibility Cheatsheet
- `backend/main.py` — FastAPI app bootstrap, startup orchestration.
- `app/core/config.py` — Environment settings, feature toggles, scraper flags.
- `app/core/database.py` — Async engine/session management.
- `app/api/v1/api.py`, `app/api/v2/api.py` — Router registration.
- `app/services/*` — Domain service logic (news, analytics, competitors, notifications, scraping).
- `app/tasks/*` — Celery task entrypoints.
- `app/scrapers/*` — Scraper strategies, config loader, rate limiting.
- `app/models/*` — SQLAlchemy models/enums for all persistence concerns.
- `alembic/versions/*` — Schema evolution history (ensure kept up to date).

---
Prepared by: GPT-5 Codex (Senior Developer mode)  
Date: 10 Nov 2025

