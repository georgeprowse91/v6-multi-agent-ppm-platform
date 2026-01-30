# Physical Architecture

## Purpose

Describe the physical deployment topology for the Multi-Agent PPM Platform, including compute tiers, storage, networking, and environment isolation.

## Architecture-level context

The platform is designed for Azure-friendly deployment with a hub-and-spoke network model, private endpoints for data services, and workload separation by environment (dev, staging, production). The physical topology maps logical services into Azure resources such as AKS, Azure Database for PostgreSQL, Redis, and Azure Service Bus.

## Physical topology (Azure reference)

- **Ingress & edge**: Azure Front Door → Application Gateway / WAF.
- **Compute**: AKS for agent services and API gateway; optional Azure Container Apps for connectors.
- **Data**: Azure Database for PostgreSQL (operational store), Azure Cache for Redis, Azure Blob Storage for documents.
- **Messaging**: Azure Service Bus for event propagation.
- **Secrets**: Azure Key Vault; managed identities for access.

## Diagram

```text
PlantUML: docs/architecture/diagrams/c4-container.puml
```

## Usage example

View the container diagram:

```bash
sed -n '1,200p' docs/architecture/diagrams/c4-container.puml
```

## How to verify

Confirm that the diagram file exists:

```bash
ls docs/architecture/diagrams/c4-container.puml
```

Expected output: the PlantUML file path.

## Implementation status

- **Implemented**: Azure infrastructure deployment scripts in `infra/terraform` and `infra/kubernetes`.

## Related docs

- [Deployment Architecture](deployment-architecture.md)
- [Infrastructure README](../../infra/README.md)
- [Security Architecture](security-architecture.md)
