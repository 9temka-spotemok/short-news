# Phase 2 — Baseline Artefacts Completion Plan

## Objective
Consolidate baseline artefacts (Playwright evidence, API ↔ client catalog updates, performance metrics) to safeguard against regressions during the frontend refactor.

## Artefact Checklist
| Artefact | Description | Owner | Location |
|----------|-------------|-------|----------|
| Playwright Baseline Report | Updated recordings/traces for analytics flows post-refactor. | Frontend QA | `frontend/playwright-report/refactor-phase2/` |
| Scenario Log | Extended `tests/phase0_playwright_baseline.md` with new scenario IDs and outcomes. | Frontend QA | `docs/REFACTORING/tests/phase0_playwright_baseline.md` |
| API ↔ Client Catalog | Link endpoints to new TanStack Query hooks and generated types. | Backend + Frontend | `docs/REFACTORING/api/phase1_endpoint_catalog.md` |
| Metrics Snapshot | LCP/CLS/FID + bundle stats captured before/after decomposition. | DevOps + Frontend | `docs/REFACTORING/metrics/phase0_baseline_metrics.md` + `metrics/performance_phase2_baseline.md` |
| Change Log Summary | Record differences vs initial baseline (improvements/regressions, dates). | PM/QA | `docs/REFACTORING/frontend/phase2_baseline_artifacts_plan.md` (append section) |

## Action Steps
1. **Playwright**
   - Re-run baseline suite (`npm run test:e2e -- --grep "@refactor-baseline"`).
   - Export trace and video artefacts; store with timestamp folder.
   - Update baseline doc with new links and observations.
2. **API Catalog**
   - Add columns `Query Hook` and `Generated Type` referencing new modules.
   - Ensure endpoints touched by refactor include note about TanStack Query adoption.
3. **Metrics**
   - Execute Lighthouse/Playwright trace capturing LCP/CLS.
   - Run bundle analysis script and record sizes.
   - Append results to `metrics/performance_phase2_baseline.md`, referencing Phase 0 metrics for comparison.
4. **Reporting**
   - Summarise findings in this document under **Results** once measurements complete.
   - Flag regressions to respective owners and create tickets if necessary.

## Timeline
- Target completion before merging decomposition and query adoption PRs.
- Re-run metrics after each major wave (filters, data hooks, component split).

## Results (to be filled)
- _Placeholder_ — update with metric deltas, scenario status, catalog completion date.

---
Prepared by: GPT-5 Codex (Senior Developer mode)  
Date: 11 Nov 2025

