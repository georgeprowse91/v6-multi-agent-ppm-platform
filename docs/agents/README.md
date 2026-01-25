# Agent Documentation

## Purpose

Provide a single entry point to the 25-agent ecosystem, including the canonical catalog, orchestration narrative, and links to the agent spec files in `agents/`.

## Architecture-level context

Agents are the decision-making layer of the platform. They are orchestrated by the Intent Router and Response Orchestrator, and they communicate with connectors and data services to deliver end-to-end PPM workflows. The orchestration flow is documented in `docs/architecture/agent-orchestration.md`.

## Key docs

- **Agent Catalog** → [agent-catalog.md](agent-catalog.md)
- **Orchestration** → [../architecture/agent-orchestration.md](../architecture/agent-orchestration.md)
- **Agent specs (implementation stubs)** → [../../agents/README.md](../../agents/README.md)

## Usage example

List all agent IDs in the catalog:

```bash
rg -n "Agent 0" docs/agents/agent-catalog.md
```

## How to verify

Confirm the catalog file exists:

```bash
ls docs/agents/agent-catalog.md
```

Expected output: the catalog file path.

## Related docs

- [Logical Architecture](../architecture/logical-architecture.md)
- [Connector Overview](../connectors/overview.md)
