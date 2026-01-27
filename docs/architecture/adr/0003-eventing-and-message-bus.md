# ADR 0003: Eventing and Message Bus

## Status

Accepted (partial implementation).

## Context

Connector syncs and workflow triggers need asynchronous signaling. The platform should support a message bus to decouple producers from consumers while still allowing local development without cloud dependencies.

## Decision

Adopt Azure Service Bus as the primary queueing mechanism for sync and event workloads, with an in-memory fallback for local development. The data sync service uses `SERVICE_BUS_CONNECTION_STRING` and `SERVICE_BUS_QUEUE` to select the Azure queue, otherwise it falls back to an in-memory queue client.

## Consequences

- Production deployments can use Service Bus for durable queueing.
- Local development does not require cloud dependencies.
- A broader event bus (topics, fanout, event contracts) remains planned.

## References

- `services/data-sync-service/src/data_sync_queue.py`
- `services/data-sync-service/src/main.py`
- `docs/api/event-contracts.md`
