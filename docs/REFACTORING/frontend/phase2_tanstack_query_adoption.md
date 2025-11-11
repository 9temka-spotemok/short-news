# Phase 2 — TanStack Query Adoption Blueprint

## Summary
- **Goal:** Introduce TanStack Query across analytics-focused flows to replace manual `useEffect` fetch sequences, improve caching, and standardise error/loading handling.
- **Scope:** Competitor Analysis feature (initial wave), with extension paths for notifications, dashboard widgets, and digest settings.
- **Key Deliverables:** Query client configuration, feature-specific hooks, shared API utilities migration, documentation updates, and testing strategy.
- **Owners:** Frontend Lead (implementation), DevEx (tooling), QA (test plan integration).

## Current State
- Global provider is already mounted in `main.tsx`, but query client uses default options and no suspense/error boundary integration.
- Pages manually orchestrate Axios calls via `src/services/api.ts`, handling loading/error locally and triggering toasts.
- Cache invalidation is manual; data duplication occurs when multiple components request the same analytics endpoints.
- Retry/backoff logic inconsistent; no standardised prefetching or background refresh.

## Target Architecture
1. **Query Client Module**
   - Create `src/lib/queryClient.ts` exporting `queryClient` instance and configuration helper.
   - Define defaults: `staleTime`, `cacheTime`, `retry`, `refetchOnWindowFocus`, logger, and suspense mode toggles.
   - Enable devtools integration gated by `import.meta.env.DEV`.

2. **Provider Integration**
   - Update `main.tsx` (or `AppProviders.tsx`) to import the shared client, wrap with `QueryClientProvider`, and conditionally attach `ReactQueryDevtools`.
   - Add error boundary + suspense boundary wrappers for route segments that rely on asynchronous data (`CompetitorAnalysisPage`, analytics dashboard).

3. **Service Layer Alignment**
   - Keep `src/services/api.ts` as single Axios source; expose typed fetchers that the hooks can delegate to.
   - Introduce helper `queryFactory()` methods or `createQueryKey` utilities to ensure consistent key composition.
   - Ensure interceptors continue to manage auth tokens/toasts; make error objects consumable by query hooks (e.g., map to `{ message, status }`).

## Hook Roadmap
| Hook | Endpoint(s) | Cache Key | Key Options | Notes |
|------|-------------|-----------|-------------|-------|
| `useAnalyticsComparison` | `/api/v2/analytics/comparison` | `["analytics", companyId, filters]` | `staleTime: 2 * 60 * 1000`, `refetchOnWindowFocus: false`, `retry: 1` | Accepts filters & comparison targets; returns formatted payload for charts. |
| `useChangeLog` | `/api/v2/analytics/change-log` | `["change-log", companyId, filters, page]` | `keepPreviousData: true`, paginated infinite query | Emits structured entries for change log list; handles empty state gracefully. |
| `useReportPresets` | `/api/v2/analytics/report-presets` | `["report-presets"]` | `staleTime: Infinity`, `enabled` based on auth | Supports create/update mutations later. |
| `useExportAnalytics` | `/api/v2/analytics/export` (mutation) | Mutation key `["analytics-export"]` | `onSuccess` triggers download util; `onError` surfaces toast | Coordinates with shared toast/error components; returns async status. |
| `usePrefetchAnalytics` | variant helper | Uses `queryClient.prefetchQuery` | Preloads analytics data on dashboard navigation | Called from router loaders or dashboard widgets. |

### Mutation Strategy
- Wrap Axios POST/PUT requests via `useMutation`.
- Centralise optimistic updates/invalidation patterns (`invalidateQueries(["analytics", ...])`).
- Provide convenience functions for invalidating subtrees (e.g., `invalidateAnalytics(companyId)`).

## Cache & Invalidation Policy
- Standardise cache keys in `src/features/competitor-analysis/queryKeys.ts` using factory functions to avoid typos.
- Adopt invalidation helpers invoked after relevant mutations (e.g., `useExportAnalytics` success).
- For filters changes, rely on query key parameters to auto-refetch.
- For background updates (e.g., when Celery tasks finish), plan to trigger invalidations via WebSocket or polling hooks (future work; align with backend events).

## Error & Loading Handling
- Use `useQuery` status flags to drive shared components:
  - `LoadingOverlay` shown when `isFetching && !isFetched`.
  - `ErrorBanner` consumes `error.message` from Axios error adapter.
- Configure global query error handler to funnel unhandled errors to toast service with consistent messaging.
- Provide `select` functions on queries to transform data once (e.g., map backend enums to UI-friendly values).

## Prefetch & Performance
- Implement `queryClient.prefetchQuery` in navigation guards (e.g., when user hovers/enters analytics route).
- Evaluate `dehydrate/rehydrate` for SSR export (future).
- Document when to use `prefetchInfiniteQuery` for paginated logs.
- Combine with lazy-loaded chart modules (todo-frontend-6) to balance initial load.

## Testing Strategy
- **Unit/Hook Tests:** Use `@tanstack/react-query` testing utilities (`QueryClientProvider` + `renderHook`) to validate success/error states, invalidation triggers, and data selectors.
- **Integration Tests:** Modify Playwright specs to assert cached data reuse (e.g., switching tabs retains analytics results).
- **Type Safety:** Ensure hooks expose typed outputs derived from shared `openapi-typescript` (future integration with task todo-frontend-8).
- **Tooling:** Add lint rule or custom ESLint guard to discourage direct `api.*` calls from components without query hooks.

## Documentation & DevEx
- Update `docs/REFACTORING/frontend/phase2_competitor_analysis_decomposition.md` references to point at specific hooks once implemented.
- Add section to root `README.md` and `docs/REFACTORING/README.md` describing TanStack Query setup, key files (`src/lib/queryClient.ts`, `src/features/.../hooks/*`), and devtools usage.
- Record onboarding notes for new hooks in `docs/FEATURES_GUIDE.md` (if available).
- Provide sample snippet in Storybook docs showing how components consume query hooks with mocked providers.

## Risk & Mitigation
- **Axios Interceptor Compatibility:** Validate that query hooks propagate 401 responses to auth store; add tests to cover refresh token workflow.
- **Race Conditions:** Ensure filters updates cancel in-flight queries via `queryClient.cancelQueries`.
- **Bundle Impact:** Monitor bundle size for `@tanstack/react-query` devtools; load lazily in dev mode only.
- **Testing Complexity:** Provide utilities (`renderWithQueryClient`) to simplify hook/component test setup.

## Rollout Checklist
1. Implement `src/lib/queryClient.ts` and update providers.
2. Create query key helpers and initial hooks (`useAnalyticsComparison`, `useChangeLog`, `useReportPresets`, `useExportAnalytics`).
3. Refactor `CompetitorAnalysisPage` to use hooks (aligned with decomposition plan).
4. Update Playwright and Vitest suites to reflect new loading/error flows.
5. Document new structure in README, refactoring docs, and Storybook notes.
6. Monitor production dashboards for cache hit improvements and LCP changes.

---
Prepared by: GPT-5 Codex (Senior Developer mode)  
Date: 11 Nov 2025

