# Phase 2 — Frontend Performance Strategy

## Objective
Quantify and improve performance of the analytics experience by applying lazy loading, intelligent prefetching, and profiling before/after the refactor.

## Key Focus Areas
1. **Bundle Optimisation**
   - Lazy-load heavy chart modules (`AnalyticsBoard`, third-party chart libs) via dynamic import.
   - Evaluate code splitting for routes using Vite’s `defineAsyncComponent` or React.lazy.
   - Confirm shared dependencies (e.g., D3 helpers) are hoisted into dedicated chunks.

2. **Data Prefetch & Caching**
   - Use `queryClient.prefetchQuery` when navigating to analytics routes.
   - Preload default filter data in dashboard landing (call `usePrefetchAnalytics`).
   - Configure background refetch intervals to balance freshness vs network load.

3. **Runtime Profiling**
   - Capture React Profiler traces before and after each migration wave (filters, hooks, components).
   - Record `useMemo`/`useCallback` hotspots and ensure dependencies stable.
   - Benchmark initial render and interactions (filter apply, export) with Chrome DevTools.

4. **Web Vitals Monitoring**
   - Measure LCP, FID, CLS using Lighthouse CI or Web Vitals script in staging.
   - Target: LCP < 2.5s, CLS < 0.1 on reference hardware (per master plan).
   - Log metrics to central dashboard; compare against baseline recorded in `metrics/phase0_baseline_metrics.md`.

5. **Network Optimisation**
   - Ensure analytics endpoints support HTTP caching headers; leverage `cacheTime` in TanStack Query.
   - Compress export payloads (gzip/brotli) and avoid redundant downloads.

## Action Plan
| Step | Task | Owner | Artefact |
|------|------|-------|----------|
| 1 | Establish baseline metrics (bundle size, LCP) | Frontend + DevOps | `metrics/performance_phase2_baseline.md` |
| 2 | Implement lazy loading for chart components | Frontend | PR + Storybook verification |
| 3 | Introduce prefetch hooks on dashboard navigation | Frontend | `usePrefetchAnalytics` hook |
| 4 | Profile interaction flows (filters, export) | Frontend | Profiler screenshots + notes |
| 5 | Re-run Lighthouse/Playwright with trace | QA | Updated artefacts in `frontend/playwright-report/perf/` |
| 6 | Document improvements + next steps | Frontend Lead | Append summary to this file |

## Tooling Recommendations
- Use `source-map-explorer` or `vite-bundle-visualizer` for bundle analysis.
- Integrate Lighthouse CI into pipeline for nightly runs.
- Add `npm run analyze` script to root README for easy bundle inspection.

## Acceptance Criteria
- Documented before/after metrics with deltas ≥20% improvement where feasible (bundle size, render time).
- Verified lazy loading (chunk splitting visible in build output).
- Prefetch strategy implemented and covered by unit/e2e tests.
- Performance report shared with stakeholders and archived in `docs/REFACTORING/metrics/`.

---
Prepared by: GPT-5 Codex (Senior Developer mode)  
Date: 11 Nov 2025

