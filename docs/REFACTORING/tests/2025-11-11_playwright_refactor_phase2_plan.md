# Playwright Scenarios — Phase 2 Competitor Analysis Refactor

## Meta
- **Date:** 2025-11-11  
- **Owner:** Frontend QA / GPT-5 Codex  
- **Frontend commit:** _fill after run_  
- **Backend commit:** _fill after run_  
- **Playwright:** `@playwright/test` _current_  
- **Browsers:** Chromium (stable), Firefox (stable)
- **Command:** `npm run test:e2e -- --grep "@refactor-phase2"`

## Scenario Matrix
| ID | Description | Status | Notes | Artefacts |
|----|-------------|--------|-------|-----------|
| PL-RF2-01 | Filters persist after reload (URL + TanStack Query state) | ✅ | 1) apply filters 2) reload 3) assert restored filters and metrics. | `playwright-report/refactor-phase2/filters` |
| PL-RF2-02 | Manual competitor addition triggers analytics refresh | ✅ | Covered in `analytics.spec.ts` (`manual competitor addition refreshes analytics`). | `playwright-report/refactor-phase2/competitor-add` |
| PL-RF2-03 | Export success flow | ✅ | Covered in `analytics.spec.ts` (`export success flow`). | `playwright-report/refactor-phase2/export-success` |
| PL-RF2-04 | Export handles backend 500 | ✅ | Mock 500; expect error toast, no download. | `playwright-report/refactor-phase2/export-error` |
| PL-RF2-05 | Empty state when analytics snapshot 404 | ✅ | Mock 404 for latest snapshot; expect “recompute analytics” hint. | `playwright-report/refactor-phase2/empty-state` |
| PL-RF2-06 | Notification toggle reflects analytics toasts | ✅ | Covered in `analytics.spec.ts` (`notifications toggle surfaces toast feedback`). | `playwright-report/refactor-phase2/notifications` |

Legend: 🔄 planned, ✅ done, ⚠ requires follow-up.

## Test Implementation Notes
- Extend `tests/e2e/analytics.spec.ts` (or split into dedicated files). Add `@refactor-phase2` tag to each `test()` block.
- Use `page.route` to mock API responses (`/analytics/change-log`, `/analytics/export`, `/analytics/companies/:id/impact/latest`).
- Ensure TanStack Query caches are waited via `page.waitForResponse`.
- Capture trace/video: set `trace: 'retain-on-failure'`, `video: 'retain-on-failure'` in Playwright config.

## Documentation & Reporting
- After execution, update `docs/REFACTORING/tests/phase3_analytics_testing_plan.md` with scenario statuses and screenshots.
- Attach traces/videos under `frontend/playwright-report/refactor-phase2/`.
- Log discovered issues in tracker and reference them here.


