# React / React Native / TypeScript Alignment Plan

## 1) Current Inventory (before alignment)

| Scope | React | React DOM | React Native | TypeScript | Peer constraints |
|---|---:|---:|---:|---:|---|
| `apps/web/frontend` | `^18.3.1` | `^18.3.1` | N/A | `^5.4.0` | via `@ppm/canvas-engine` |
| `apps/mobile` | `18.2.0` | N/A | `0.73.6` | `~5.3.3` | Expo SDK 50 runtime stack |
| `packages/canvas-engine` | peer `^18.0.0` | peer `^18.0.0` | N/A | `^5.4.0` (dev) | `react`, `react-dom` peers |

Source manifests: `apps/web/frontend/package.json`, `apps/mobile/package.json`, `packages/canvas-engine/package.json`.

## 2) Compatibility Target Matrix

### Chosen baseline

- **React:** `18.2.0`
- **React DOM:** `18.2.0`
- **React Native:** `0.73.6` (unchanged, Expo SDK 50 compatible)
- **TypeScript:** `5.3.3`

### Why this target

- Mobile (Expo 50) was already pinned to React 18.2 / RN 0.73; this is the strongest compatibility anchor.
- Web and shared package can safely run on React 18.2 and do not require React 18.3-only APIs.
- TypeScript 5.3.3 keeps parity with mobile template expectations and avoids split compiler behavior across apps.

### Alignment changes applied

- `apps/web/frontend`
  - `react` + `react-dom` now use workspace catalog (`18.2.0` source of truth).
  - `@types/react`, `@types/react-dom`, and `typescript` now use workspace catalog.
- `apps/mobile`
  - `react`, `@types/react`, `typescript` now use workspace catalog.
- `packages/canvas-engine`
  - peers tightened to `>=18.2.0 <19`.
  - `@types/react`, `@types/react-dom`, `typescript` now use workspace catalog.
- `pnpm-workspace.yaml`
  - added `apps/mobile` as a workspace package.
  - added a **catalog** section as workspace version policy source of truth.

## 3) Changelog-based Risk Review + Smoke Test Plan

### Risk review

- **React 18.3.x -> 18.2.0 (web downgrade):**
  - Primary risk is if code relies on 18.3 warning behavior or subtle scheduler internals.
  - Mitigation: run web build/typecheck/tests and manually validate core rendering routes.
- **TypeScript 5.4 -> 5.3.3 (web/shared downgrade):**
  - Risk of losing 5.4 parser/type-system behavior (notably around inference edge cases).
  - Mitigation: run strict typecheck in web and shared package to catch regressions.
- **Peer tightening in canvas-engine (`>=18.2 <19`):**
  - Intended to make expectations explicit and prevent accidental React 19 adoption before validation.
  - Mitigation: install-time peer checks and existing tests.
- **Workspace enrollment of mobile:**
  - Potential lockfile churn and cross-workspace dependency resolution changes.
  - Mitigation: run `pnpm install` and smoke app-specific scripts.

### Smoke test plan

1. Install + lockfile refresh: `pnpm install`.
2. Web validation:
   - `pnpm --filter @ppm/web-ui typecheck`
   - `pnpm --filter @ppm/web-ui test`
   - `pnpm --filter @ppm/web-ui build`
3. Shared package validation:
   - `pnpm --filter @ppm/canvas-engine typecheck`
   - `pnpm --filter @ppm/canvas-engine test`
4. Mobile validation:
   - `pnpm --filter ppm-mobile start -- --non-interactive` (or local Expo start smoke)
   - optional platform smoke: `android` / `ios` if runners available.

## 4) Ongoing Drift Prevention Policy

1. **Workspace catalog authority**
   - React/TypeScript family versions are defined in `pnpm-workspace.yaml` catalog.
   - Consumers should reference `catalog:` entries instead of ad-hoc semver ranges.
2. **Renovate grouping**
   - `.github/renovate.json` groups React + TS stack updates into a single PR.
   - Prevents partial upgrades that break cross-app compatibility.
3. **Peer constraint guardrails**
   - Shared packages declare explicit compatible React ranges (`>=18.2.0 <19`).
4. **Release hygiene**
   - For any React/RN/TS major or minor bump, require:
     - change-log review,
     - matrix confirmation across web + mobile + shared packages,
     - smoke test execution from this document.
