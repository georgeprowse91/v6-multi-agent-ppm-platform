# Notification Service endpoint reference

Source: `services/notification-service/src/main.py`

| Method | Path | Handler |
| --- | --- | --- |
| `GET` | `/healthz` | `healthz` |
| `POST` | `/v1/notifications/predictive-alerts` | `send_predictive_alert` |
| `POST` | `/v1/notifications/send` | `send_notification` |
| `GET` | `/version` | `version` |
