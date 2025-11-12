# Phase 2 — Frontend Documentation Update Plan

## Objective
Ensure all documentation (README, Storybook, refactoring files) reflects the new feature-first structure, TanStack Query hooks, and testing practices introduced during the frontend refactor.

## Documentation Targets
| Artifact | Updates Required | Owner | Notes |
|----------|-----------------|-------|-------|
| Root `README.md` | Add section “Frontend Feature Modules” with mapping of key directories (`src/features/competitor-analysis`, `src/lib/queryClient.ts`, testing commands). | Frontend Lead | ✅ 11 Nov 2025 — добавлен раздел “Feature-модуль Competitor Analysis”, отражающий новые файлы и интеграцию TanStack Query. |
| `docs/REFACTORING/README.md` | Maintain navigation to new frontend docs (decomposition, TanStack Query, testing, performance). | Documentation Coordinator | Already partially updated; confirm after each new plan is added. |
| `docs/FEATURES_GUIDE.md` | Document feature responsibilities, exported hooks, and integration points (auth store, toasts). | Frontend Lead | Create cross-links to API catalog entries. |
| Storybook Docs (MDX) | Provide usage notes for major components (`FiltersPanel`, `AnalyticsBoard`, `ChangeLog`, `ExportModal`). | Design Systems | Outline data requirements and sample query hooks usage. |
| API Catalog (`api/phase1_endpoint_catalog.md`) | Reference new hooks for each endpoint; add column “Query Hook” linking to implementation. | Backend + Frontend | Supports todo-frontend-9 baseline alignment. |
| Testing Plans | Append QA acceptance results to `tests/phase3_analytics_testing_plan.md`; link to Playwright reports. | QA Lead | Sync with phase2 testing plan outcomes. |

### Storybook Integration Snippet

```tsx
// .storybook/preview.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const storybookQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
      staleTime: 60 * 1000,
    },
  },
})

export const decorators = [
  (Story) => (
    <QueryClientProvider client={storybookQueryClient}>
      <Story />
    </QueryClientProvider>
  ),
]
```

## Communication Plan
- Publish changelog in engineering channel summarising doc updates.
- Schedule knowledge share session for frontend team (30 min) with walkthrough of new architecture and documentation locations.
- Update onboarding checklist to include reading new feature docs and running Storybook.

## Tooling & Automation
- Introduce lint rule or CI check ensuring README references stay valid (run `npm run lint:links` if available).
- Add script to regenerate Table of Contents where applicable (use `doctoc` or similar).

## Timeline
1. **Before code migration:** Draft README changes, create placeholders in Storybook docs.
2. **During migration:** Update documentation in lockstep with feature module landings.
3. **Post-migration:** Conduct doc review with stakeholders, archive meeting notes in `docs/REFACTORING/meetings/`.

## Acceptance Criteria
- All referenced files exist and contain up-to-date content.
- Storybook docs accessible via `/docs` tab with accurate props and sample code.
- Root README clearly describes new commands and architecture, preventing confusion for new contributors.
- API catalog includes hook references to avoid drift between backend endpoints and frontend usage.

---
Prepared by: GPT-5 Codex (Senior Developer mode)  
Date: 11 Nov 2025

