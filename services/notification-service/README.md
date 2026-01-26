# Notification Service

The notification service renders templates and delivers notifications through a dev adapter. It is
structured so production adapters (email/Slack/etc.) can be added via environment configuration.

## Contracts

- OpenAPI: `services/notification-service/contracts/openapi.yaml`
- Templates: `services/notification-service/templates/*.txt`

## Run locally

```bash
python -m tools.component_runner run --type service --name notification-service
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `NOTIFICATION_TEMPLATES_DIR` | `services/notification-service/templates` | Template directory |
| `NOTIFICATION_OUTBOX_DIR` | `services/notification-service/outbox` | File delivery directory for non-stdout channels |
| `LOG_LEVEL` | `info` | Logging verbosity |
| `PORT` | `8080` | HTTP port for the service |

## Example request

```bash
curl -X POST http://localhost:8080/notifications/send \
  -H "Content-Type: application/json" \
  -d '{
    "template": "welcome",
    "variables": {
      "recipient_name": "Morgan",
      "event_name": "Stage Gate Approved",
      "event_time": "2025-01-01T00:00:00Z"
    },
    "channel": "stdout",
    "recipient": "morgan@example.com"
  }'
```

## Tests

```bash
pytest services/notification-service/tests
```
