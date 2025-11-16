# Phase 2 — Frontend QA & Testing Expansion

## Objective
Deliver a coordinated QA plan for the refactored competitor analysis feature set, ensuring the TanStack Query migration and component decomposition are covered by automated tests (Vitest + Playwright) and manual acceptance criteria.

## Scope
- Hooks and utilities introduced in `features/competitor-analysis`.
- Shared API layer changes (query fetchers, mutation adapters).
- UI components (filters panel, analytics board, change log, export modal).
- Regression flows tied to analytics data, notifications, and exports.

## Responsibilities
| Role | Owner | Deliverables |
|------|-------|--------------|
| Frontend QA Lead | TBD | Playwright scenario updates, baseline artefacts, regression sign-off |
| Frontend Engineers | TBD | Vitest coverage implementation, Storybook stories |
| DevEx | TBD | Testing utilities, CI integration |

## Vitest Coverage Targets
| Module | Tests | Notes |
|--------|-------|-------|
| `useFiltersState` | reducer cases, URL sync, reset behaviour | Mock `searchParams` utilities |
| `useAnalyticsComparison` | success/error states, selectors, cancellation | Use MSW/axios-mock-adapter |
| `useChangeLog` | pagination, empty state, error fallback | Validate `keepPreviousData` handling |
| `useReportPresets` | stale data reuse, enabled flag, edge errors | Ensure auth gating respected |
| `useExportAnalytics` | mutation success/error, invalidation triggers | Mock download helper |
| UI компоненты | Snapshot + interaction тесты (React Testing Library для основных веток фильтров/метрик). | `FiltersPanel`, `PersistentMetricsBoard`, `ChangeEventsSection`, `ExportModal`, `CompanyAnalysisFlow`, `custom-analysis/AnalyticsTabs`, `custom-analysis/PresetManager`. |
| Shared formatters/mappers | unit tests per formatter + snapshot for chart data | Align with todo-frontend-7 |

- Create `renderHookWithClient` helper to wrap tests with `QueryClientProvider`.
- Enforce minimum 80% statement coverage on `features/competitor-analysis/**/hooks`.

## Playwright Enhancements
- **Existing Baseline:** Extend `tests/e2e/analytics.spec.ts` to utilise new selectors and confirm caching behaviour.
- **New Scenarios:**
  1. Filters persistence across navigation (URL sync + reload).
  2. Manual competitor addition → analytics refresh (ensures queries invalidate).
  3. Notification subscription changes (if UI touches analytics toasts).
  4. Export flow success & error fallback (mock backend 500).
  5. Empty state rendering when analytics API returns 404.
- Capture trace/video for each scenario; store under `frontend/playwright-report/refactor-phase2/`.
- Update `docs/REFACTORING/tests/phase0_playwright_baseline.md` with new scenario IDs referencing this plan.

## Storybook & Visual Regression
- Add stories for `FiltersPanel`, `AnalyticsTabs`, `PresetManager`, `CompanyAnalysisFlow`, `CompanySelectionStep`, `CompetitorSuggestionStep`, `AnalysisResultsStep`.
- Integrate Chromatic (or Playwright snapshot mode) to catch regressions.
- Document knobs/controls for mocking TanStack Query data.

## CI Integration
- Update CI pipeline to run `npm run test:unit -- --coverage` and Playwright suites tagged `@refactor-phase2`.
- Add PR checklist item: “Vitest + Playwright updated for analytics refactor changes”.

## Acceptance Criteria
1. Vitest suites cover all new hooks/utilities with green run in CI.
2. Playwright scenarios pass locally and in CI with artefacts archived.
3. Storybook stories documented and referenced in README.
4. QA sign-off doc appended to `docs/REFACTORING/tests/phase3_analytics_testing_plan.md`.

## Timeline
- **Week 1:** Implement testing utilities, update vitest suites for filters + analytics hook.
- **Week 2:** Complete Playwright scenario updates, add export/empty state coverage.
- **Week 3:** Storybook stories + visual diffs, CI hardening, acceptance sign-off.

---
Prepared by: GPT-5 Codex (Senior Developer mode)  
Date: 11 Nov 2025

