# Logical Architecture

## Purpose

Explain how logical components (agents, orchestration, data services, and connectors) collaborate to deliver the Multi-Agent PPM Platform capabilities.

## Architecture-level context

The logical architecture organizes the platform into three logical planes:

1. **Engagement plane** (API gateway, web prototype) in `apps/`.
2. **Decision plane** (agent orchestration + domain agents) in `agents/`.
3. **Integration and data plane** (connectors, data schemas, lineage) in `integrations/connectors/` and `data/`.

These planes are orchestrated through intent routing, task planning, and policy enforcement. Each domain agent owns canonical data entities and publishes events consumed by other agents or analytics workflows.

## Key components

- **Intent Router (Agent 01)**: classifies user intent and routes to domain agents.
- **Response Orchestrator (Agent 02)**: builds multi-step plans and composes responses.
- **Domain agents (Agents 03–25)**: own specific PPM domain processes (see the [Agent Catalog](../agents/agent-catalog.md)).
- **Connector runtime**: translates between canonical schemas and external APIs.
- **Data services**: enforce schema validation, lineage capture, and quality scoring.

## Diagram

```text
PlantUML: docs/architecture/diagrams/c4-component.puml
```

Supplementary service interaction diagram:

```text
PlantUML: docs/architecture/diagrams/service-topology.puml
```

## Usage example

Inspect the component diagram source:

```bash
sed -n '1,200p' docs/architecture/diagrams/c4-component.puml
```

## How to verify

Check that the logical architecture file references the agent catalog:

```bash
rg -n "Agent Catalog" docs/architecture/logical-architecture.md
```

Expected output: a reference to `docs/agents/agent-catalog.md`.

## Implementation status

- **Implemented**: agent runtime scaffolding, API gateway, and orchestration service.
- **Implemented**: workflow engine integration and domain agent registrations in `services/agent-runtime/`.

## Related docs

- [Agent Catalog](../agents/agent-catalog.md)
- [Agent Orchestration](agent-orchestration.md)
- [Data Architecture](data-architecture.md)
