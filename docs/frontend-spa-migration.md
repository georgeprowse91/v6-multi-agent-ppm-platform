# Frontend SPA Migration Map

## State and routing baseline

- Primary console is `apps/web/frontend` mounted under `/app`.
- Global state uses Zustand with:
  - `session` (auth + user)
  - `tenantContext` (active tenant id/name)
  - feature flags and UI state
- Route guards enforce:
  - `RequireAuth` for all application routes
  - `RequireTenantContext` for tenant-scoped pages
  - `RequireAdminRole` for `/admin/*`

## Legacy route compatibility

Legacy UI pages in `apps/web/static` are no longer served by runtime compatibility switches.

Legacy endpoints now always redirect to SPA routes.

## Migration completion status

- Migration is finalized and legacy UI is retired.
- `/v1/ui/migration-map` now publishes `migration_status.legacy_ui_retired: true` as the stable completion signal for API consumers.
- Legacy workspace shell compatibility is fully removed; `/workspace` and `/v1/workspace` are retired.

## Route migration table

| Legacy route | SPA route | Compatibility note |
| --- | --- | --- |
| `/v1/approvals` | `/app/approvals` | Approval UI moved into SPA workflows module. |
| `/v1/workflow-monitoring` | `/app/workflows/monitoring` | Monitoring route remains realtime-capable in SPA. |
| `/v1/document-search` | `/app/knowledge/documents` | Knowledge docs search consolidated under SPA knowledge. |
| `/v1/lessons-learned` | `/app/knowledge/lessons` | Lessons moved into SPA knowledge navigation. |
| `/v1/audit-log` | `/app/admin/audit` | Admin-only route now protected by admin role guard. |

## Final state: `/workspace` is retired

- `GET /workspace` and `GET /v1/workspace` are permanently retired and return `404`.
- The legacy static workspace shell is removed and is not part of runtime routing behavior.
- API compatibility remains for backend endpoints (`/v1/api/*`, `/api/workspace/*`) that the SPA consumes.

## Post-migration contract

Supported SPA entrypoints:

- `/app`
- `/app/projects/:projectId`
- `/portfolio/:portfolioId`, `/portfolios/:portfolioId`
- `/program/:programId`, `/programs/:programId`
- `/project/:projectId`, `/projects/:projectId`

Explicitly unsupported legacy routes:

- `/workspace`
- `/v1/workspace`
- legacy workspace HTML/query-string entrypoints tied to the retired static shell

### Communication and deprecation timeline

- Publish retirement confirmation for `/workspace` behavior to users and integrators.
- Include timeline checkpoints:
  - announcement date
  - reminder window(s)
  - final retirement date already completed
- Link migration mapping (`/v1/ui/migration-map`) and supported `/app/*` equivalents in all communications.

## Realtime integration baseline

- Frontend subscribes to realtime channels via websocket (`/ws/events`) using tenant + user context.
- Channels consumed:
  - `workflow_status`
  - `approval_update`
  - `notification`
- Realtime events are normalized in `useRealtimeStore` and consumed by workflow, approvals, and notification views.

## E2E journeys covered

Critical journey tests assert route accessibility and guard behavior for:

- login route
- dashboard/home
- approvals
- prompt manager/config pages
- connector marketplace/status path
