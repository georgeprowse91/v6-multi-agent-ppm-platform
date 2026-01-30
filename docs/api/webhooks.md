# Webhooks

## Purpose

Define webhook conventions and document the current implementation status.

## Current implementation status

Webhook endpoints are available for supported connectors. Connector syncs still fall back to polling and explicit `/sync/run` requests in the Data Sync Service when webhooks are not configured or supported.

## Endpoint

`POST /api/v1/connectors/{connector_id}/webhook`

The endpoint accepts JSON payloads from external systems. Webhooks are only accepted when the connector is enabled.

### Authentication & signatures

Webhook requests must include either:

- `X-Webhook-Secret`: a shared secret configured in the API gateway via `CONNECTOR_<CONNECTOR_ID>_WEBHOOK_SECRET`, **or**
- `X-Webhook-Signature`: an HMAC SHA-256 signature of the raw request body, formatted as `sha256=<hex_digest>`.

Requests without a valid secret or signature are rejected.

### Headers

| Header | Description |
| --- | --- |
| `X-Webhook-Secret` | Shared secret for direct comparison. |
| `X-Webhook-Signature` | HMAC SHA-256 signature for payload integrity. |
| `X-Tenant-ID` | Optional tenant identifier for audit logging. |

### Example

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: $CONNECTOR_JIRA_WEBHOOK_SECRET" \
  -d '{"webhookEvent": "jira:issue_updated", "issue": {"key": "ENG-42"}}' \
  https://api.example.com/api/v1/connectors/jira/webhook
```

## Registration workflow

When a connector is activated, the API gateway attempts to register the webhook endpoint with the external service (if the connector provides a registration handler). The URL it provides is:

```
{base_url}/api/v1/connectors/{connector_id}/webhook
```

If a connector does not support webhooks or a secret is not configured, polling remains the fallback mechanism.

## Verification steps

- Confirm current sync entry points:
  ```bash
  rg -n "/sync/run" services/data-sync-service/src/main.py
  ```

## Related docs

- [Connector Overview](../connectors/overview.md)
- [Data Sync Failures Runbook](../runbooks/data-sync-failures.md)
