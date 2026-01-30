# Connector & Integration Architecture

## Purpose

Define how the Multi-Agent PPM Platform integrates with enterprise systems, including authentication, canonical mapping, sync strategy, conflict resolution, and connector certification.

## Architecture-level context

Connectors sit between domain agents and external systems of record. They translate canonical schemas in `data/schemas/` into system-specific payloads, enforce auth policies, and emit lineage/quality metadata for every sync. Connector metadata is stored in the registry at `connectors/registry/`.

## Connector lifecycle

1. **Register**: add a manifest in `connectors/<name>/manifest.yaml` and list it in `connectors/registry/connectors.json`.
2. **Map**: create mapping YAMLs under `connectors/<name>/mappings/` for each entity.
3. **Authenticate**: configure auth profile based on `connectors/registry/schemas/auth-config.schema.json`.
4. **Sync**: use the connector runner to pull/push canonical entities.
5. **Certify**: execute the certification checklist and attach evidence.

## Authentication patterns

- **OAuth 2.0 / OIDC** (preferred): configured per connector with refresh token handling.
- **API tokens**: stored in vault and scoped to the connector.
- **Service accounts**: for systems that only support basic auth.

Auth configuration lives in environment-specific files under `config/` and is referenced by connector manifests.

## Mapping approach

Mappings are declarative YAML that map canonical fields to external system fields. The mapping engine applies transformations (enum, date, currency) and emits quality scores.

**Example mapping file**: `connectors/jira/mappings/project.yaml`

## Sync strategy and conflict resolution

- **Sync modes**: read-only, write-only, bi-directional.
- **Incremental sync**: change data capture based on updated timestamps.
- **Conflict resolution**: configurable policies (source-wins, platform-wins, manual review).

Connector sync telemetry is recorded as lineage artifacts under `data/lineage/`.

## Certification process

The certification checklist is defined in [docs/connectors/certification.md](certification.md) and includes:

- Schema validation and mapping coverage
- Auth and rate-limit handling
- Functional tests in sandbox environments
- Security review and secrets handling

## Diagram

```text
PlantUML: docs/architecture/diagrams/seq-connector-sync.puml
```

## Usage example

Inspect the Jira connector manifest:

```bash
sed -n '1,120p' connectors/jira/manifest.yaml
```

## How to verify

Validate the connector registry lists Jira:

```bash
rg -n "jira" connectors/registry/connectors.json
```

Expected output: a JSON entry for Jira with a manifest path.

## Implementation status

- **Implemented**: connector runtime logic, OAuth2 refresh handling, and registry coverage for Jira, Planview, Clarity, ServiceNow, and SAP.
- **In progress**: register and certify the remaining packaged connectors (Azure DevOps, Salesforce, SharePoint, Slack, Teams, Workday).

## Related docs

- [Connector README](../../connectors/README.md)
- [Data Model](../data/README.md)
- [Security Architecture](../architecture/security-architecture.md)
