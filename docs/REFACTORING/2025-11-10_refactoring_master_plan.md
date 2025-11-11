# Refactoring Master Plan — 10 Nov 2025

## Executive Summary
- **Objective:** Deliver a coordinated backend + frontend refactor that improves readability, quality, performance, and extensibility while fixing known defects and reducing technical debt.
- **Foundation:** Detailed pre-refactor assessments in:
  - `docs/REFACTORING/2025-11-10_backend_pre_refactoring_report.md`
  - `docs/REFACTORING/2025-11-10_frontend_pre_refactoring_report.md`
- **Execution tracker:** `docs/REFACTORING/2025-11-10_refactoring_backlog.md` (пофазовый backlog задач, синхронизируемый с трекером команды).

## Owners & Contacts _(заполнить в рамках X-001)_
| Направление | Ответственный | Канал связи |
|-------------|---------------|-------------|
| Backend     | _TBD_         | _TBD_       |
| Frontend    | _TBD_         | _TBD_       |
| QA          | _TBD_         | _TBD_       |
| DevOps      | _TBD_         | _TBD_       |
- **Vision:** Transform AI Competitor Insight Hub into a modular platform with clear domain boundaries, automated migrations, resilient analytics workflows, and a modernised UI architecture ready for rapid iteration and expansion.

## Goals & Success Metrics
| Goal | Success Criteria |
| ---- | ---------------- |
| Improve readability & comprehension | Module-level documentation, cyclomatic reduction in key services/pages (>25% decrease), onboarding guide updated. |
| Increase quality & reliability | ✅ All migrations auto-run; ✅ Critical flows covered by regression tests; ✅ Error budgets defined for key APIs. |
| Accelerate development & support | Mean PR lead time < 2 days; Storybook (or equivalent) in place; scripts for common tasks (`make lint`, `make test`). |
| Boost performance | API P95 < 400 ms; analytics recompute throughput +20%; frontend LCP < 2.5 s on target hardware. |
| Reduce technical debt | Debt register documented; top 5 items closed; raw SQL hotspots replaced; monolithic components decomposed. |
| Improve flexibility & scalability | Feature flag framework; analytics & notification services expose interfaces; env configuration unified. |
| Fix known bugs | Migration skip removed; Telegram 409 conflicts regression-tested; `/companies/scan` overrides stabilised. |
| Provide new system vision | Strategic roadmap documented (see “Future Evolution”), aligning data, analytics and collaboration surfaces. |

## Current State Snapshot
- **Backend:** Strong domain coverage but migrations disabled, services interwoven, observability limited. See backend pre-refactoring report for detail.
- **Frontend:** Rich functionality but large monolithic pages, minimal unit testing, duplicated types. See frontend pre-refactoring report.
- **Infrastructure:** Docker-compose baseline, Redis/Postgres/Celery worker stack; CI pipelines exist but need reinforcement to handle new tests.

## Refactoring Strategy (Phased)
1. **Stabilisation (Week 1–2)**
   - Reinstate Alembic migrations with safe startup guard.
   - Capture baseline metrics, establish monitoring dashboards.
   - Freeze API contracts (OpenAPI snapshot) and record UI workflows via Playwright.
2. **Domain Decomposition (Week 3–5)**
   - Backend: Segment services into bounded contexts (News, Analytics, Notifications, Competitor Intelligence). Introduce clear interfaces + new module layout.
   - Frontend: Split `CompetitorAnalysisPage` into feature modules with hooks; migrate API calls to TanStack Query.
3. **Quality & Performance (Week 6–7)**
   - Expand pytest + vitest coverage; integrate with CI.
   - Optimise analytics recompute path; add caching and instrumentation.
   - Implement React Suspense/Error Boundaries for protected routes.
4. **Extensibility & Vision (Week 8+)**
   - Introduce feature flag framework.
   - Implement design tokens/theme system.
   - Prepare shared schema tooling (OpenAPI → TypeScript generation).

## Backend Workstream
- **Migrations & Config**
  - Restore `apply_migrations()` with fallback detection.
  - Document enum update workflow (DB + TS alignment).
  - Centralise env validation (single boot guard, script compatibility).
- **Service Refactor**
  - Extract interfaces for analytics, notifications, scrapers.
  - Replace residual raw SQL with SQLAlchemy Core/ORM.
  - Implement repository layer or query objects for complex fetches.
- **Task Orchestration**
  - Add idempotency guards to Celery tasks.
  - Instrument dynamic schedule loader with metrics (success/fail counts).
  - Provide CLI commands for manual replays (reuse dependency injection per Context7 guidance).
- **Observability & Testing**
  - Integrate structured logging, add Celery + FastAPI instrumentation (OpenTelemetry/Prometheus).
  - Expand integration tests for `/api/v2/analytics/*`, competitor diff recompute, notifications dispatch.

## Frontend Workstream
- **Architecture**
  - Introduce feature-first folder structure (`src/features/*`).
  - Create domain hooks (`useAnalyticsComparison`, `useCompetitorChangeLog`) leveraging TanStack Query.
  - Add context or store modules for shared filters/state.
- **UI Refactor**
  - Break competitor analysis UI into renderers (filters panel, comparison board, analytics timeline, change log).
  - Normalise formatting utilities (dates, currency, priority).
  - Implement reusable toast/error banner components.
- **Quality**
  - Author vitest suites for API service wrappers and critical hooks.
  - Extend Playwright coverage (authenticate, add competitor, recompute analytics, export).
  - Add Storybook (optional) or alternative to document core components.
- **Performance**
  - Lazy-load heavy chart modules.
  - Pre-fetch frequently used data on dashboard entry.
  - Evaluate React profiler results post-decomposition.

## Cross-cutting Tasks
- **Contract Management:** Generate shared types from OpenAPI (Foundational task to prevent backend/frontend drift).
- **Documentation:** Update README, `docs/FEATURES_GUIDE.md`, and new refactoring docs per milestone. Provide file responsibility matrix (already in pre-reports).
- **DevEx:** Introduce Makefile/Taskfile for consistent commands. Update Docker compose to include new services or watchers if required.
- **Security:** Ensure JWT rotation, rate limiting, and security headers validated post-refactor. Coordinate with `docs/ANALYSIS/04_SECURITY_ANALYSIS.md`.

## Risk Management
| Risk | Mitigation | Owner |
| ---- | ---------- | ----- |
| Schema drift during migration re-enable | Run migrations on staging clone first; add rollback script. | Backend Lead |
| API contract regressions | Snapshot OpenAPI, add contract tests in CI. | QA Lead |
| UI behavioural changes | Baseline via Playwright/visual snapshots; product review gates. | Frontend Lead |
| Timeline creep | Track tasks in roadmap board with WIP limits; weekly burndown review. | PM |
| Performance regressions | Establish performance benchmarks; run after each major merge. | DevOps |

## Future Evolution (Beyond Refactor)
- **Data Platform:** Evolve analytics engine to support multi-tenant workspaces, user-defined metrics, integration with BI tools. Consider event-driven ingestion for real-time updates.
- **Collaboration:** Build shared dashboards, annotations, and alerting rules per team. Extend notifications to Slack/webhooks with templating.
- **Intelligence Layer:** Introduce recommender system for competitor insights, leverage LLM summarisation with guardrails, integrate knowledge graph visualisation UI.
- **Extensibility:** Package analytics & notification modules as reusable SDKs; open partner API.
- **Operational Excellence:** Implement SLO tracking, canary deployments, blue/green release strategy.

## Next Steps
1. Align stakeholders on plan (engineering, product, data science).
2. Create detailed backlog mapped to phases; assign owners.
3. Schedule migration reinstatement dry-run.
4. Kick off architecture workshops for backend and frontend teams.
5. Begin Stabilisation phase tasks; update status weekly in shared tracker.

---
Prepared by: GPT-5 Codex (Senior Developer mode)  
Date: 10 Nov 2025

