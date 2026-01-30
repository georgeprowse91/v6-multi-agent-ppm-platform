# ADR 0006: Data Lineage and Audit

## Status

Accepted (partial implementation).

## Context

The platform needs traceability for data flowing from connectors through agents to storage. Audit logs must be immutable and retained based on classification policies.

## Decision

- Use JSON lineage artifacts under `data/lineage/` to document source-to-target transformations.
- Implement an audit log service that validates events against `data/schemas/audit-event.schema.json`, applies retention policies from `config/retention/policies.yaml`, and stores events in immutable storage.

## Consequences

- Local development can rely on example lineage artifacts and local encrypted WORM storage.
- Production deployments can use Azure Blob WORM storage via environment configuration.
- Data sync services emit lineage events to the data-lineage service for supported connectors (for example, Jira sync jobs).

## References

- `data/lineage/example-lineage.json`
- `services/audit-log/src/main.py`
- `services/audit-log/src/audit_storage.py`
- `docs/data/lineage.md`
