# Phase 2 — Competitor Analysis Decomposition Plan

## Summary
- **Goal:** Break down `frontend/src/pages/CompetitorAnalysisPage.tsx` into feature-oriented modules that align with the refactoring master plan (tasks F-201, F-202, F-203, F-301, F-401).
- **Outcome:** Clear feature boundaries, reusable hooks/components, and a migration playbook that preserves current behaviour while enabling TanStack Query adoption and test coverage expansion.
- **Owners:** Frontend Lead (implementation), Frontend QA (tests), Design Systems/Platform (Storybook & docs).

## Current Pain Points
- **Monolithic structure:** ~2.8k LOC blending routing, state, data fetching, and rendering logic.
- **Ad-hoc state management:** Multiple `useState`/`useEffect` islands; duplicated fetch flows; manual loading/error handling.
- **Tight coupling:** UI, data mappers, and side-effects (toasts, exports) intertwined, making regression risk high.
- **Limited testability:** Hard to isolate business logic for unit tests; no component stories or hook tests.

## Target Architecture
```
frontend/src/
└── features/
    └── competitor-analysis/
        ├── hooks/
        │   ├── useFiltersState.ts
        │   ├── useAnalyticsComparison.ts        // TanStack Query
        │   ├── useChangeLog.ts                  // TanStack Query
        │   ├── useReportPresets.ts              // TanStack Query
        │   └── useExportAnalytics.ts
        ├── components/
        │   ├── FiltersPanel/
        │   ├── AnalyticsBoard/
        │   ├── ChangeLog/
        │   ├── ExportModal/
        │   └── LayoutShell/
        ├── utils/
        │   ├── formatters.ts                    // shared formatters
        │   └── mappers.ts                       // API → UI transforms
        ├── state/
        │   └── filtersStore.ts                  // Zustand or context reducer
        ├── types.ts                             // feature-scoped types
        ├── index.ts                             // feature facade
        └── tests/
            ├── hooks/
            └── components/
```
- **Page refocus:** `src/pages/CompetitorAnalysisPage.tsx` becomes a thin orchestrator that composes feature modules.
- **Shared resources:** Utilities promoted to `src/lib/formatters` and reused by other features (F-203).

## Migration Waves
| Wave | Scope | Deliverables | Dependencies | Acceptance Criteria |
|------|-------|--------------|--------------|---------------------|
| 1. Skeleton | Create `features/competitor-analysis` structure, stub exports, add barrel file. | Directory scaffold, Storybook placeholder, initial README entry. | None. | App builds unchanged; page still imports legacy code. |
| 2. Filters | Move filter state + UI into `FiltersPanel`, wire dedicated hook/store. | `useFiltersState`, `FiltersPanel` component, vitest coverage for reducers. | Wave 1. | Page consumes new hook; legacy filter code removed; tests green. |
| 3. Analytics Data | Introduce TanStack Query hooks (`useAnalyticsComparison`, `useChangeLog`, `useReportPresets`). | Query client config (shared `src/lib/queryClient.ts`), provider adjustments, hook tests. | Wave 2, Task F-202. | Data fetching uses query hooks; loading/error states handled via reusable banner. |
| 4. Rendering Modules | Split analytics board, change log, export modal into components with props typed via new feature types. | `AnalyticsBoard`, `ChangeLog`, `ExportModal` components, Storybook stories. | Wave 3. | Components covered by snapshot/interaction tests; page composes new pieces. |
| 5. Exports & Side-effects | Extract export flow (`useExportAnalytics`), centralise toast/error handling, hook into unified utilities. | Shared toast component, export hook tests, documentation updates. | Wave 4, Task F-203. | No direct `toast.*` calls in page; utilities reused across feature. |
| 6. Clean-up & Removal | Remove remaining legacy helpers, ensure tree-shaking/route-level code splitting where applicable. | Lazy loading for charts, updated Playwright specs, final README updates. | Waves 1–5, Task F-302. | Bundle size diff recorded; Playwright regression run passes. |

## Progress (11 Nov 2025)
- ✅ Wave 1 scaffolded: `frontend/src/features/competitor-analysis/{constants.ts,index.ts,types.ts}` плюс утилита `utils/filterPayload.ts`.
- ✅ Wave 2 (filters) в работе: внедрены `hooks/useFiltersState.ts` и `components/FiltersPanel.tsx`, `CompetitorAnalysisPage` переключён на новый хук/компонент; legacy фильтровый код удалён.
- ✅ Начат вынос change-log: добавлены `hooks/useChangeEvents.ts` + интеграция на странице через TanStack Query.
- ✅ Вынесены крупные секции: `PersistentMetricsBoard` и `CurrentSignalsBoard` теперь живут в `features/competitor-analysis/components/*`; вкладка **Persistent Metrics** и **Current Signals** подключают их напрямую.
- ✅ Страница переключена на `useCompanyAnalyticsInsights` (TanStack Query) вместо `loadAnalyticsInsights`: снапшоты, временные ряды и knowledge graph подтягиваются через фичевый хук и разделяют кэш между компонентами.
- ✅ Создан компонент `CompanyDeepDive.tsx`, который инкапсулирует Brand Preview, BI, распределения тем/тональности и сравнение объёма новостей; `CompetitorAnalysisPage` теперь передаёт данные через фасад вместо ручного JSX.
- ✅ Режим Company Analysis вынесен в `CompanyAnalysisFlow.tsx`, а сводка активных фильтров переиспользуется через `ActiveFiltersSummary.tsx`; страница стала тоньше и выступает только координатором. Компонент остаётся «one-click» сценарием: пользователь выбирает компанию, запускает анализ, а подбор конкурентов происходит автоматически через `useAnalysisFlow`.
- ✅ Шаги Custom Analysis (`CompanySelection`, `CompetitorSuggestion`, `AnalysisResults`) вынесены в `features/competitor-analysis/components/custom-analysis/*`; главная страница переключает их как визард, а выбор режима реализован `AnalysisModeSelection.tsx`.
- ✅ Analytics вкладки и менеджер пресетов вынесены в `custom-analysis/AnalyticsTabs.tsx` и `custom-analysis/PresetManager.tsx`; `CompetitorAnalysisPage` теперь просто передаёт стейт и колбэки.
- ✅ Impact панель вынесена в `components/ImpactPanel.tsx`; отображение метрик и knowledge graph теперь полностью управляется фичевым компонентом.
- ✅ Вспомогательные хелперы вынесены в `utils/comparisonPayload.ts`: генерация payload для TanStack Query и экспорта теперь переиспользуется между вкладками и download-флоу.
- ✅ Логика сравнения инкапсулирована в `hooks/useComparisonManager.ts`: загрузка сравнения, переключение периодов и выбор A/B теперь реализованы в фичевом хуке, страница лишь вызывает действия.
- ✅ Управление состоянием анализа вынесено в `hooks/useAnalysisFlow.ts`: выбор компаний, выполнение анализа и управление ошибками/спиннерами теперь сосредоточены в одном фичевом хуке.
- ✅ Добавлены фичевые фасады (`queryKeys.ts`, `useChangeLog`, `useKnowledgeGraph`, `usePrefetchAnalytics`, `useReportPresetActions`, `useAnalyticsExportHandler`); страница пользуется готовыми хуками вместо локальных обработчиков.
- ✅ Унифицированы состояния загрузки/ошибок через `frontend/src/components/ErrorBanner.tsx` и `frontend/src/components/LoadingOverlay.tsx`; `ChangeEventsSection`, `PersistentMetricsBoard`, `ImpactPanel` и мастеринг подсказок используют единую визуализацию.
- ℹ️ Следующие шаги — покрытие e2e/Storybook по новому плану (Wave 3–4).

## State & Data Strategy
- **Filters:** Adopt reducer-based store (Zustand slice or React context) to manage query params, persisted in URL via `useSearchParams`.
- **Analytics payloads:** TanStack Query configured with `keepPreviousData`, `staleTime` tuned for dashboard usage, and dedicated cache keys (`["analytics", companyId, filters]`).
- **Error/Loading UI:** Shared `ErrorBanner` and `LoadingOverlay` components consumed by feature modules; error boundaries at route level.
- **Exports:** Side-effects (download triggers) isolated in hook with service adapter; success/error feedback uses unified toast component.

## Testing Plan (Alignment with F-301 & F-302)
- **Unit/Hook tests:** Vitest suites for filters reducer, query hooks (mocking API client), export hook.
- **Component tests:** Storybook stories, visual regression snapshots for `AnalyticsBoard` states, Chromatic (optional).
- **E2E:** Update Playwright specs to cover filters persistence, change log pagination, export success/error flows.
- **Performance baselines:** Capture LCP/CPU profile before/after Waves 3 & 6; document in `metrics/`.

## Documentation & DevEx
- Update `docs/REFACTORING/README.md` and repo root `README.md` with feature module description, key files, and scripts (`npm run storybook`, `npm run test:unit`).
- Add feature-level README (co-located) detailing responsibilities and public API (facade exports).
- Note TanStack Query guidelines in `docs/REFACTORING/api/phase1_endpoint_catalog.md` once hooks map to endpoints.

## Risks & Mitigations
- **Contract drift:** Coordinate with backend on analytics payload changes; leverage OpenAPI → TS generation task (B-402/Future).
- **Regression risk:** Each wave gated by unit + e2e checks; maintain feature flags if staged rollout needed.
- **Performance surprises:** Monitor React Profiler, ensure lazy-loading doesn't regress UX (prefetch critical data using `queryClient.prefetchQuery`).

## Definition of Done
- Legacy `CompetitorAnalysisPage` reduced to feature composition with <200 LOC.
- Feature folder exports clearly documented and used by other modules.
- TanStack Query adopted for all analytics-related data fetching in the page.
- Vitest and Playwright coverage thresholds agreed with QA met.
- README and refactoring docs updated; backlog tasks F-201, F-202, F-203, F-301 flagged as ✅ ready for implementation hand-off.

---
Prepared by: GPT-5 Codex (Senior Developer mode)  
Date: 11 Nov 2025

