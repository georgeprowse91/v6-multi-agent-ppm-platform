# Solution Index

## Purpose

Provide a concise inventory of the solution documentation in this repository, highlight coverage by pillar, and flag gaps that require follow-up work. This index links the end-to-end platform narrative described in `README.md` and `docs/README.md`.

## Architecture-level context

The Multi-Agent PPM Platform documentation is organized by solution pillars (architecture, agents, methodologies, connectors, data, security/compliance, and operations). Each pillar maps to a dedicated doc set under `docs/` and to concrete artifacts under `agents/`, `connectors/`, `data/`, `infra/`, and `services/`. This index links those materials so readers can trace high-level concepts to concrete implementation assets.

## Documentation inventory by pillar

| Pillar | Key docs (source of truth) | What it covers | Status |
| --- | --- | --- | --- |
| Architecture | `docs/architecture/system-context.md`, `docs/architecture/logical-architecture.md`, `docs/architecture/physical-architecture.md`, `docs/architecture/deployment-architecture.md` | System context, logical/physical layers, deployment on Azure | Implemented (narratives + diagrams) |
| Agents & Orchestration | `docs/architecture/agent-orchestration.md`, `docs/agents/agent-catalog.md` | Orchestration flow, catalog of 25 agents | Implemented (docs + runtime scaffolding) |
| Methodologies | `docs/methodology/overview.md`, `docs/methodology/agile/`, `docs/methodology/waterfall/`, `docs/methodology/hybrid/` | Methodology maps, gates, templates | Implemented (docs + templates) |
| Connectors & Integrations | `docs/connectors/overview.md`, `docs/connectors/supported-systems.md` | Integration architecture, connector principles, maturity | Implemented (Planview, Clarity, SAP, Workday, Salesforce, Slack, Teams, ServiceNow connectors now covered) |
| Data Model, Quality & Lineage | `docs/architecture/data-architecture.md`, `docs/data/`, `data/schemas/` | Canonical schemas, data architecture | Implemented (schemas + example lineage/quality) |
| Security & Compliance | `docs/architecture/security-architecture.md`, `docs/compliance/` | RBAC/ABAC, threat model, retention | Implemented (docs + enforcement) |
| Observability/Resilience/Performance | `docs/architecture/observability-architecture.md`, `docs/architecture/resilience-architecture.md`, `docs/architecture/performance-architecture.md` | Monitoring, failure modes, performance targets, SLA-driven load harness | Implemented (targets + load validation against staging/production) |
| Product & UX | `docs/product/solution-overview/README.md`, `docs/product/` | Vision, requirements, personas | Partial (go-to-market narratives; implementation details in architecture docs) |
| Deployment & Ops | `infra/README.md`, `docs/runbooks/` | Terraform and runbooks | Implemented (runbooks + environment guidance) |

## Gaps and next steps

- Maintain certification evidence for connector coverage as new integrations ship.
- Add production-grade event bus documentation once event contracts are finalized.
- Provide UI walkthroughs when the web console evolves beyond the current lightweight implementation.

## Usage example

Open the docs hub and follow the reading order:

```bash
open docs/README.md
```

## How to verify

Run the documentation link check:

```bash
python scripts/check-links.py
```

Expected output: no lines printed and exit code 0.

## Related docs

- [Docs Hub](README.md)
- [Solution Overview](product/solution-overview/README.md)
- [Architecture Docs](architecture/README.md)
