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

## Route migration table

| Legacy route | SPA route | Compatibility note |
| --- | --- | --- |
| `/v1/approvals` | `/app/approvals` | Approval UI moved into SPA workflows module. |
| `/v1/workflow-monitoring` | `/app/workflows/monitoring` | Monitoring route remains realtime-capable in SPA. |
| `/v1/document-search` | `/app/knowledge/documents` | Knowledge docs search consolidated under SPA knowledge. |
| `/v1/lessons-learned` | `/app/knowledge/lessons` | Lessons moved into SPA knowledge navigation. |
| `/v1/audit-log` | `/app/admin/audit` | Admin-only route now protected by admin role guard. |
| `/v1/workspace?demo=true` | `/app` | Legacy workspace shell replaced by SPA shell. |

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
