# Documentation Hub

## Purpose

This hub guides enterprise stakeholders through the Multi-Agent PPM Platform blueprint, from product vision to architecture, agent orchestration, integrations, data, and operations. It links the canonical docs and concrete repo assets that make the solution implementable.

## Architecture-level context

The documentation set is organized around the solution pillars that mirror the platform architecture:

- **Experience layer** (apps and UX concepts) → `apps/`, `docs/product/`
- **Orchestration and agent ecosystem** → `agents/`, `docs/agents/`, `docs/architecture/agent-orchestration.md`
- **Integration and data fabric** → `connectors/`, `data/`, `docs/connectors/`, `docs/data/`
- **Security/compliance and operations** → `docs/compliance/`, `docs/runbooks/`, `infra/`

Each pillar contains narratives and concrete artifacts (schemas, manifests, YAML maps) that are referenced from these docs.

## Golden path (non-coder reading order)

1. **Solution Overview** → [docs/product/solution-overview/README.md](product/solution-overview/README.md)
2. **Solution Index (current-state diagnosis)** → [docs/solution-index.md](solution-index.md)
3. **System Context & Architecture** → [docs/architecture/system-context.md](architecture/system-context.md)
4. **Agent Catalog + Orchestration** → [docs/agents/agent-catalog.md](agents/agent-catalog.md)
5. **Methodology Maps** → [docs/methodology/overview.md](methodology/overview.md)
6. **Connectors & Integration Model** → [docs/connectors/overview.md](connectors/overview.md)
7. **Data Model, Quality, Lineage** → [docs/data/README.md](data/README.md)
8. **Security & Compliance** → [docs/architecture/security-architecture.md](architecture/security-architecture.md)
9. **Observability, Resilience, Performance** → [docs/architecture/observability-architecture.md](architecture/observability-architecture.md)
10. **Deployment & Operations** → [infra/README.md](../infra/README.md)

## Usage examples

Open the docs locally in your browser:

```bash
open docs/README.md
```

Generate a quick overview of the agent catalog:

```bash
rg -n "Agent 01" docs/agents/agent-catalog.md
```

## How to verify

Validate internal markdown links:

```bash
python scripts/check-links.py
```

Expected output: no lines printed and exit code 0.

## Related docs

- [Root README](../README.md)
- [Architecture Docs](architecture/README.md)
- [Connector Registry](../connectors/registry/connectors.json)
- [Data Schemas](../data/schemas/)
