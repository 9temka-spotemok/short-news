# Phase 2 — Utilities & Toast System Unification

## Objective
Standardise formatting, data mapping, and toast/error handling across the frontend to support the decomposed feature modules and TanStack Query adoption.

## Deliverables
- **Shared Utilities Package**
  - Create `src/lib/formatters/` for date, currency, priority, and status helpers.
  - Introduce `src/lib/mappers/analytics.ts` to transform backend payloads into chart-ready structures.
  - Provide unit tests for each formatter/mapper (see testing plan).
- **Toast & Error Components**
  - Build reusable `ToastProvider` (or extend existing library) with consistent variants (`success`, `error`, `info`, `warning`).
  - Create `ErrorBanner` and `InlineError` components for page-level and component-level feedback.
  - Expose helper `useToast()` hook centralising success/error messages.
- **Integration with TanStack Query**
  - Configure global query error handler to route Axios errors through `useToast`.
  - Replace ad-hoc `toast.*` calls in pages/components with the new API.
  - Ensure mutation hooks return structured error objects consumable by UI.

## Migration Steps
1. Inventory existing formatter functions (spread across components) using `frontend_pre_refactoring_report` references.
2. Move canonical implementations into `src/lib/formatters`, export via barrel file.
3. Update components to import from new location; add ESLint rule to prevent local formatter duplicates.
4. Implement toast provider and wrap app in `AppProviders.tsx`.
5. Replace manual toast calls in competitor analysis feature; document patterns for other features.

## Testing & QA
- Vitest suites for formatters/mappers (snapshot and explicit value checks).
- Component tests for `ErrorBanner` and toast provider integration (ensuring accessibility).
- Playwright scenarios verifying toasts appear once per error, vanish appropriately, and no duplicate notifications occur.

## Documentation
- Update `docs/FEATURES_GUIDE.md` with formatter/toast usage guidelines.
- Add Storybook entries demonstrating error states and toast variants.
- Reference this plan in TanStack Query blueprint for error handling alignment.

## Acceptance Criteria
- No direct `toast.*` calls outside of `useToast` or provider context.
- All analytics-related components consume shared formatters/mappers.
- Toast/error components documented and covered by tests.
- ESLint or code review checklist updated to enforce the conventions.

---
Prepared by: GPT-5 Codex (Senior Developer mode)  
Date: 11 Nov 2025

