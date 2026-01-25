# Architecture Documentation

## Purpose

Provide the canonical architecture narratives and diagrams for the Multi-Agent PPM Platform, with direct links to the implementation assets in this repository.

## Architecture-level context

The architecture docs explain how the platform delivers AI-native portfolio management through layered services (apps, orchestration, connectors, data, and operations). Diagrams live under `docs/architecture/diagrams/` and are referenced by the narrative documents.

## Key documents

- **System context** → [system-context.md](system-context.md)
- **Logical architecture** → [logical-architecture.md](logical-architecture.md)
- **Physical architecture** → [physical-architecture.md](physical-architecture.md)
- **Deployment architecture** → [deployment-architecture.md](deployment-architecture.md)
- **Agent orchestration** → [agent-orchestration.md](agent-orchestration.md)
- **Security architecture** → [security-architecture.md](security-architecture.md)
- **Observability architecture** → [observability-architecture.md](observability-architecture.md)

## Usage examples

Open the system context diagram source:

```bash
sed -n '1,80p' docs/architecture/diagrams/c4-context.puml
```

## How to verify

List available diagram sources:

```bash
ls docs/architecture/diagrams
```

Expected output includes `c4-context.puml`, `c4-container.puml`, and `c4-component.puml`.

## Related docs

- [Agent catalog](../agents/agent-catalog.md)
- [Connector overview](../connectors/overview.md)
- [Data model & lineage](../data/README.md)
