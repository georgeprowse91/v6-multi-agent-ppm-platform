# Notification Service

Email/chat notification templates and delivery scaffolding.

## Current state

- Helm chart under `services/notification-service/helm/`.
- Templates stored in `services/notification-service/templates/`.
- No outbound delivery implementation yet.

## Quickstart

Validate the Helm chart:

```bash
python scripts/validate-helm-charts.py services/notification-service/helm
```

## How to verify

```bash
ls services/notification-service/templates
```

Expected output includes notification template files.

## Key files

- `services/notification-service/templates/`: message templates.
- `services/notification-service/src/`: service scaffolding.
- `services/notification-service/helm/`: deployment assets.

## Example

Search for template subjects:

```bash
rg -n "subject" services/notification-service/templates
```

## Next steps

- Implement delivery handlers in `services/notification-service/src/`.
- Connect to workflow triggers in `apps/workflow-engine/`.
