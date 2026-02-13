# Mobile App Source

Source code for the React Native mobile application.

## MVP feature boundaries

The current MVP intentionally focuses on the minimum flow needed for executive portfolio visibility and approval actioning from a mobile device:

- **In scope**
  - Authenticated app shell backed by API gateway session + OIDC tokens.
  - Approval inbox with approve/reject actions.
  - Read-only portfolio/project dashboard snapshot.
  - Status submission queue that works offline and retries when connectivity returns.
  - Push notification handling for approval events with deep-link routing into the approval area.
- **Out of scope (post-MVP)**
  - Rich editing for project/canvas entities.
  - Multi-step approval comments/escalations.
  - Background sync beyond status queue replay.
  - Advanced notification preferences and inbox history.

## Product backlog (MVP slices)

1. **Approval actions**
   - Surface pending approvals from `/api/workflows/approvals`.
   - Enable explicit approve/reject actions via the API gateway.
   - Refresh inbox state after action submission.
2. **Portfolio snapshot**
   - Deliver read-only portfolio summary, project health, and KPIs.
   - Keep dashboard resilient when partial payloads are missing.
3. **Status submit queue**
   - Persist queued status updates locally.
   - Replay queue on reconnect and manual retry.
   - Track replay failures via retry count.

## Directory structure

| Folder | Description |
| --- | --- |
| [api/](./api/) | API client |
| [components/](./components/) | Reusable UI components |
| [context/](./context/) | React context providers |
| [i18n/](./i18n/) | Internationalization |
| [screens/](./screens/) | Screen components |
| [services/](./services/) | Secure storage, telemetry, notifications, and sync queues |

## Key files

| File | Description |
| --- | --- |
| `theme.ts` | Application theme definitions |
