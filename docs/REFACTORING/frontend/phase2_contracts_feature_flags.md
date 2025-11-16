# Phase 2 — API Contracts & Feature Flags Alignment

## Objective
Synchronise frontend type generation with backend OpenAPI artifacts and define a strategy for consuming feature flags in the refactored UI.

## Type Generation Strategy
- Adopt `openapi-typescript` (or alternative per DevEx recommendation) to generate TypeScript definitions from `openapi.json`.
- Store generated types under `frontend/src/generated/openapi.ts` (Git-tracked with versioning).
- Add npm script `npm run generate:types` invoking backend script + generator.
- Hook generation into CI (fail if diff not committed) to maintain contract parity.
- Update `src/services/api.ts` and TanStack Query hooks to consume generated types instead of manual enums.
- Document mapping between generated types and feature modules (e.g., `CompetitorComparisonResponse` → `useAnalyticsComparison`).

## Feature Flag Integration
- Coordinate with backend feature flag framework (see backend tasks B-401).
- Implement lightweight flag provider in frontend:
  - `src/lib/featureFlags/FeatureFlagProvider.tsx` reads flag payload from `/api/v1/feature-flags` (or configuration endpoint).
  - Expose `useFeatureFlag(key)` hook returning flag state with optional default.
- Support build-time toggles via `import.meta.env` for experimental features.
- Ensure flags are serialised in analytics queries to allow backend experimentation.

## Rollout Plan
1. Backend generates updated `openapi.json` (existing CI step).
2. Add frontend script to consume schema and regenerate types.
3. Refactor competitor analysis hooks to rely on generated types.
4. Introduce feature flag provider and wrap application providers.
5. Document flag contracts and usage examples in README and feature docs.

## Testing
- Add unit tests to ensure generated types compile with current code (e.g., type-only import usage checks).
- Mock feature flag responses in Storybook and Playwright to verify variant rendering.
- Validate fallback behaviour when flag endpoint unavailable (graceful defaults).

## Documentation
- Update `api/phase1_endpoint_catalog.md` with column “Generated Type” referencing type names.
- Create flag registry appendix in `docs/FEATURES_GUIDE.md` enumerating available flags and owners.
- Note generation commands in root README and developer onboarding docs.

## Acceptance Criteria
- Type generation script integrated into developer workflow with clear instructions.
- No manual duplication of backend enums; `src/types/index.ts` either references generated types or is deprecated.
- Feature flag provider in place with at least one pilot flag covering analytics experiments.
- Docs updated and linked from refactoring README.

---
Prepared by: GPT-5 Codex (Senior Developer mode)  
Date: 11 Nov 2025

