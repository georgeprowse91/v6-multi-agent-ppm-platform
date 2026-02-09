# Notification Service: Templates

## Purpose

Document the templates assets owned by the Notification Service service.

## What's inside

- `services/notification-service/templates/welcome.txt`: Text asset used by this component.
- `services/notification-service/templates/portfolio-intake.txt`: Portfolio intake notification message.
- `services/notification-service/templates/intake-triage-summary.txt`: Intake triage summary message.
- `services/notification-service/templates/agent-run-status.txt`: Agent run status notification message.

## How it's used

These assets are consumed by the service runtime or deployment tooling.

## How to run / develop / test

```bash
ls services/notification-service/templates
```

## Configuration

Configuration is inherited from the parent service and `.env` settings.

## Troubleshooting

- Missing asset files: ensure the parent service references valid paths.
- Validation failures: confirm schema compatibility with the parent service.
