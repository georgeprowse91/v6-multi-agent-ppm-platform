# Webhooks

## Purpose

Define webhook conventions and document the current implementation status.

## Current implementation status

Webhook endpoints are **not yet implemented** in the platform runtime. Connector syncs currently run via polling and explicit `/sync/run` requests in the Data Sync Service. Webhook support is planned for the Connector Hub and notification services.

## Proposed conventions

When webhook support is added, use the following conventions:

- **Endpoint structure:** `/webhooks/{provider}/{event}`
- **Headers:** Include `X-Signature` for payload integrity and `X-Tenant-ID` for tenant routing.
- **Payload format:** JSON with `event_id`, `timestamp`, `tenant_id`, and provider-specific payload fields.
- **Retries:** Exponential backoff for 5xx responses; 4xx responses should not retry unless explicitly flagged.

## Planned integration points

- **Connector Hub:** Register webhook configurations alongside connector metadata.
- **Notification service:** Emit outbound webhooks to downstream systems when configured.
- **Audit log service:** Record webhook delivery events as audit records.

## Verification steps

- Confirm current sync entry points:
  ```bash
  rg -n "/sync/run" services/data-sync-service/src/main.py
  ```

## Related docs

- [Connector Overview](../connectors/overview.md)
- [Data Sync Failures Runbook](../runbooks/data-sync-failures.md)
