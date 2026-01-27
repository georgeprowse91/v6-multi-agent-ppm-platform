# ADR 0007: Connector Certification

## Status

Accepted.

## Context

Connectors integrate with external systems and must meet security, data quality, and operational standards before production enablement. Certification evidence should be tracked alongside connector metadata.

## Decision

Adopt a manual certification checklist documented in `docs/connectors/certification.md` and track status in `connectors/registry/connectors.json`. Connector manifests, mappings, and tests serve as evidence artifacts.

## Consequences

- Certification status is transparent in the registry.
- Manual evidence collection is required until automated tooling is added.
- Connector onboarding includes explicit validation steps and approvals.

## References

- `docs/connectors/certification.md`
- `connectors/registry/connectors.json`
- `connectors/registry/schemas/connector-manifest.schema.json`
