# Services

This directory contains supporting services that run alongside the core applications. Services are
intended to be deployed independently and communicate via APIs and events.

## Included services
- **audit-log**: Long-term audit trail and retention storage for platform events.
- **data-sync-service**: Background synchronisation for connector data and reconciliation rules.
- **identity-access**: IAM, RBAC enforcement, and tenant identity integration.
- **notification-service**: Email/chat notifications and templated communications.
- **policy-engine**: Policy evaluation and enforcement for compliance rules.
- **telemetry-service**: Central ingestion and processing of logs, metrics, and traces.

## Implementation notes
Service folders include placeholders for `src`, `helm`, `tests`, and other deployment artifacts.
Populate them as each service is implemented.
