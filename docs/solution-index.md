# Solution Index (Phase 1)

## Purpose

Provide a concise inventory of the solution documentation in this repository, highlight coverage by pillar, and flag gaps that require follow-up work. This index is the starting point for the end-to-end blueprint described in `README.md` and `docs/README.md`.

## Architecture-level context

The Multi-Agent PPM Platform documentation is organized by solution pillars (architecture, agents, methodologies, connectors, data, security/compliance, and operations). Each pillar maps to a dedicated doc set under `docs/` and to concrete artifacts under `agents/`, `connectors/`, `data/`, `infra/`, and `services/`. This index links those materials so readers can trace high-level concepts to concrete implementation assets.

## Documentation inventory by pillar

| Pillar | Key docs (source of truth) | What it covers | Status |
| --- | --- | --- | --- |
| Architecture | `docs/architecture/system-context.md`, `docs/architecture/logical-architecture.md`, `docs/architecture/physical-architecture.md`, `docs/architecture/deployment-architecture.md` | System context, logical/physical layers, deployment on Azure | Partial (narratives + diagrams are being expanded) |
| Agents & Orchestration | `docs/architecture/agent-orchestration.md`, `docs/agents/agent-catalog.md` | Orchestration flow, catalog of 25 agents | Implemented (docs only; runtime remains partial) |
| Methodologies | `docs/methodology/overview.md`, `docs/methodology/agile/`, `docs/methodology/waterfall/`, `docs/methodology/hybrid/` | Methodology maps, gates, templates | Implemented (docs + templates) |
| Connectors & Integrations | `docs/connectors/overview.md`, `connectors/README.md` | Integration architecture, connector principles | Partial (Jira example complete; others planned) |
| Data Model, Quality & Lineage | `docs/architecture/data-architecture.md`, `docs/data/`, `data/schemas/` | Canonical schemas, data architecture | Implemented (schemas + example lineage/quality) |
| Security & Compliance | `docs/architecture/security-architecture.md`, `docs/compliance/` | RBAC/ABAC, threat model, retention | Implemented (docs; enforcement planned) |
| Observability/Resilience/Performance | `docs/architecture/observability-architecture.md`, `docs/architecture/resilience-architecture.md`, `docs/architecture/performance-architecture.md` | Monitoring, failure modes, performance targets | Implemented (targets documented) |
| Product & UX | `docs/product/solution-overview/README.md`, `docs/product/` | Vision, requirements, personas | Partial (needs repo-specific walkthroughs) |
| Deployment & Ops | `infra/README.md`, `docs/runbooks/` | Terraform and runbooks | Partial (DR narrative + env matrix needed) |

## Missing/weak pillars (targeted in this blueprint)

- Agent catalog and orchestration flow are not documented as a single end-to-end narrative.
- Methodology maps exist but lack “what the YAML means” and example workflows.
- Connector documentation lacks manifest, mapping, and certification artifacts.
- Data lineage and data quality artifacts are not present.
- Security posture and compliance mapping are not separated into implemented vs planned coverage.
- Observability and resilience docs lack explicit SLO/SLI targets and degradation modes.

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
