# Frontend Pre-refactoring Report — 10 Nov 2025

## Scope & Baseline
- **Context:** React 18 + Vite + TypeScript frontend located in `frontend/`.
- **Baseline version:** 0.1.0 (per `package.json`).
- **Artifacts reviewed:** routing (`App.tsx`), pages, components, services (`src/services/api.ts`), state store (`src/store/authStore.ts`), types, configs (Vite, Tailwind), tests, build scripts.
- **Goal:** Document current UI architecture, data flow, and risk factors to support a safe refactor that boosts clarity, reliability, performance, and long-term scalability.

## Architecture Overview
- **Entry point:** `main.tsx` mounts `<App />`; wraps in React Router, TanStack Query provider, Tailwind styles.
- **Routing:** `App.tsx` defines public vs protected routes. Protected routes guarded by Zustand auth store flags (`isAuthenticated`). Layouts:
  - `Layout` (public: includes header/footer).
  - `DashboardLayout` (private: side navigation, no footer).
- **Pages:** 14 route modules under `src/pages/`. Key ones:
  - `DashboardPage`, `CompetitorAnalysisPage`, `NewsAnalyticsPage` for analytics views.
  - `DigestSettingsPage`, `SettingsPage`, `NotificationsPage` for user preferences.
  - `AuthNewsPage`, `GuestNewsPage`, `CategoryDetailPage` for news browsing.
  - `LoginPage`, `RegisterPage`, `ProfilePage` for auth flows.
- **Components:** Shared UI primitives under `src/components/` (charts, selectors, export menus, team insights, etc.). Tailwind classes heavily used, sometimes combined with custom formatting functions.
- **State management:** Zustand store `authStore.ts` (persisted to localStorage) handles auth tokens/user. Most other state handled via `useState` inside pages. TanStack Query not yet leveraged for data fetching except provider setup (opportunity).
- **Styling:** Tailwind + custom CSS in `index.css`. Component-specific classes embedded inline.
- **Build & tooling:** Vite 5, TypeScript 5.6, ESLint 9, Prettier 3, Tailwind 3.4. Scripts for lint, format, type-check, vitest, Playwright e2e.

## Data & API Integration
- **HTTP layer:** `src/services/api.ts` centralises Axios instances (`api` for `/api/v1`, `apiV2` for `/api/v2`). Interceptors handle auth headers, console logging in dev, toast-based error handling with granular status mapping.
- **Typed contracts:** `src/types/index.ts` mirrors backend enums/schemas (news categories, analytics enums, competitor change statuses, export payloads). Some duplication vs backend models—needs sync strategy.
- **Key service methods:** 
  - News operations (`getNews`, `searchNews`, mark read/favourite).
  - Auth flows (`login`, `register`, `refreshToken`, `logout`).
  - Company management (`getCompanies`, `scanCompany`, `createCompany`, subscribe/unsubscribe).
  - Analytics v2 endpoints (`fetchComparison`, `exportAnalysis`, knowledge graph retrieval).
  - Competitor diff recompute, report presets CRUD.
- **Error handling:** Standardised toast messaging; analytics 404s suppressed to allow empty states. Need to ensure future refactors preserve interceptors contract expected by pages.
- **Env handling:** `VITE_API_URL` optional, fallback to Vite proxy. Additional envs used by tests (Playwright) captured in docs.

## UI & Interaction Notes
- **CompetitorAnalysisPage:** Single file >2,800 LOC with complex state machine handling filters, analytics fetches, diff recomputation, export, A/B comparisons. Candidate for decomposition (hooks, context, subcomponents).
- **AddCompetitorModal:** Multi-step wizard for manual competitor addition (scan, preview, confirm). Integrates with backend scanning service; ensure asynchronous states preserved.
- **Charts & analytics components:** `ImpactTrendChart`, `MultiImpactTrendChart`, `MarketPosition`, `ThemeAnalysis` rely on D3-like data shaping and consistent analytics payload. Refactor should abstract data mappers to avoid duplication.
- **Notification center & settings:** `TrackedCompaniesManager`, `NotificationCenter` rely on store state and API service for subscription updates; consider centralising query hooks with TanStack Query for caching and optimistic updates.
- **Internationalisation:** None implemented; UI text baked into components (English). Document plan if localisation becomes requirement.

## Quality & Testing
- **Unit tests:** `src/pages/__tests__` currently empty; vitest configured but minimal coverage. Significant over-reliance on manual testing.
- **E2E:** Playwright spec `frontend/tests/e2e/analytics.spec.ts` covers recompute → export flow. Ensure e2e updated alongside refactor.
- **Linting/type-check:** ESLint + TypeScript; need to enforce during CI after refactor. Check for suppressed warnings (none obvious).
- **Accessibility:** Tailwind classes provide baseline but no global accessibility strategy; evaluate for future enhancements.

## Technical Debt & Risk Summary
| Area | Impact | Notes |
| ---- | ------ | ----- |
| Monolithic pages | **High** | `CompetitorAnalysisPage` and similar modules difficult to reason about; risk introducing regressions during refactor. |
| State sprawl | High | Many `useState` islands; lack of centralised query cache or context leads to duplicated fetch logic and stale state handling. |
| API coupling | Medium | Frontend depends on specific response shapes (e.g. analytics export payload). Need contract tests or shared schema. |
| Error handling | Medium | Toasts hide underlying errors; consider surfacing structured error components for reliability. |
| Testing gaps | Medium | Vitest available but not used; limited regression safety net. |
| Performance | Medium | Heavy pages fetch multiple payloads sequentially; potential to parallelise with TanStack Query & Suspense in refactor. |
| Type duplication | Medium | Enums replicated manually; risk drift from backend. Consider codegen from OpenAPI or shared package. |
| Auth persistence | Low/Medium | Zustand persist stores tokens in localStorage without expiration checks. Ensure refresh flow robust during refactor. |

## Refactoring Opportunities (Aligned with Goals)
- **Readability & Maintainability:** Break large pages into feature modules (e.g. `/features/analytics`, `/features/notifications`) with dedicated hooks (`useCompetitorAnalytics`, `useNotificationSettings`). Adopt folder-by-feature structure.
- **Reliability:** Introduce TanStack Query for data with caching, loading/error states, retries. Wrap protected routes with suspense & error boundaries. Add vitest suites for service utilities and hooks.
- **Performance:** Parallelise API requests (Promise.allSettled already used in some places) via query hooks. Memoise expensive computations (`useMemo` used but ensure dependencies accurate). Investigate dynamic imports for heavy analytics components.
- **Developer Velocity:** Add code generation for TypeScript types from backend OpenAPI. Introduce Storybook or component playground for isolated UI development.
- **Technical Debt Reduction:** Centralise toast/error contracts, extract filter management from `CompetitorAnalysisPage` into dedicated hook/service. Replace inline formatters with shared utilities (e.g. `formatPriority`, `formatCurrency`).
- **Flexibility & Scalability:** Design UI state machines for competitor analysis (mode/step) using state charts or reducer pattern to support future scenarios (multi-mode analytics). Encapsulate export builder flows to support new formats.
- **Bug Fixing:** Audit manual DOM manipulations; ensure forms handle validation errors gracefully (currently limited). Implement route-level guards to prevent navigation with unsaved changes where relevant.

## Cross-cutting Considerations
- **Backend contracts:** Tight coupling with analytics v2 endpoints—coordinate refactor with backend API changes (e.g. knowledge graph, change logs). Document in final report.
- **Design consistency:** Tailwind classes scattered; consider design tokens or theme config to ensure consistent spacing/colour usage.
- **Feature flags:** No frontend flag framework; rely on backend toggles. Future work: integrate simple flag provider to control experimental UI.

## Immediate Watchlist Before Major Refactor
1. Catalogue all API calls in `ApiService` and map to backend endpoints; note required auth scopes.
2. Capture UX baselines (screenshots via Playwright) for visual regression comparison.
3. Inventory global state requirements beyond auth (filters, analytics results) to plan store/query migration.
4. Document critical workflows (competitor comparison, export) for QA sign-off.
5. Align with design / product on potential UX adjustments (e.g. filter panels, multi-step wizards) prior to code restructuring.

## File Responsibility Cheatsheet
- `src/App.tsx` — Router + providers setup.
- `src/services/api.ts` — Axios instances, API methods, error interception.
- `src/types/index.ts` — Domain types mirroring backend schemas.
- `src/store/authStore.ts` — Zustand-based auth persistence.
- `src/pages/CompetitorAnalysisPage.tsx` — Core analytics UI (needs decomposition).
- `src/components/*` — Shared visual components (charts, selectors, layout).
- `vite.config.ts`, `tsconfig*.json` — Build and compiler configuration.
- `playwright.config.ts`, `tests/e2e/*` — E2E scaffold.

---
Prepared by: GPT-5 Codex (Senior Developer mode)  
Date: 10 Nov 2025




