# Connector Maturity Rubric (Level 0-3)

This rubric defines implementation expectations for connector manifests (`integrations/connectors/*/manifest.yaml`) and CI quality gates.

## Level definitions

### Level 0 — Registered only
- Manifest exists and validates.
- Connector can be discovered/loaded.
- No guaranteed read/write/webhook support.

### Level 1 — Read-ready
- Level 0 requirements.
- Read sync path implemented for at least one resource.
- Declarative mappings exist for declared resources.
- Basic mapping/runtime validation passes.

### Level 2 — Bidirectional production baseline
- Level 1 requirements.
- Read + write sync implemented for primary resources.
- Idempotency strategy defined and implemented.
- Conflict handling strategy defined and implemented.
- Conformance tests pass in SDK harness.

### Level 3 — Operationally hardened
- Level 2 requirements.
- Webhook/event support (or explicit documented exception).
- Health metrics and sync lag visibility.
- Error-budget/SLO instrumentation and runbook references.

## Manifest metadata

Each connector manifest includes a `maturity` section:

- `level` (`0`–`3`)
- `tier` (`candidate`, `core`, `strategic`)
- `business_priority` (`1` highest)
- `capabilities` (`read`, `write`, `webhook`, `declarative_mapping`, `idempotent_write`, `conflict_handling`)
- `notes` (short rationale)

## Current priority cohort

Top-priority Level 2 cohort for this phase:

1. `jira`
2. `azure_devops`
3. `servicenow`
4. `salesforce`
5. `workday`
6. `sap`
7. `slack`
8. `teams`
9. `outlook`
10. `smartsheet`
