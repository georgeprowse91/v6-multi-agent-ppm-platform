# Agent Orchestration

## Purpose

Describe how the platform routes user intent, plans multi-step workflows, executes tool calls, and composes responses across the 25-agent ecosystem.

## Architecture-level context

Agent orchestration sits between the experience layer (`apps/`) and domain agents (`agents/`). It coordinates intent detection, guardrails, memory/state, connector access, and response composition. The catalog of agent responsibilities is defined in the [Agent Catalog](../agents/agent-catalog.md).

## Orchestration flow

1. **Intent routing**: the Intent Router agent classifies the user request and selects candidate agents.
2. **Plan creation**: the Response Orchestration agent builds a multi-step plan and enforces policy guardrails.
3. **Tool execution**: Domain agents invoke connectors and data services using canonical schemas.
4. **State management**: Results are stored in short-term state (request context) and long-term knowledge (data/lineage).
5. **Response composition**: the Response Orchestration agent synthesizes a final response and cites source data.

## Guardrails and escalation

- **Policy guardrails**: RBAC/ABAC checks before tool execution.
- **Safety gates**: approvals required for high-impact actions (budget changes, scope changes).
- **Escalation**: if confidence is low or data is missing, the Approval Workflow agent (The Approval Workflow agent) requests human input.

## Event bus

Agent coordination relies on an event bus abstraction that can publish/subscribe to orchestration
topics. Production deployments use Azure Service Bus topics via the shared
`packages/event-bus` package, which exposes an async API for publishing messages and listening on
subscriptions. The in-memory bus remains available for local development and unit testing.

## Sequence diagram (example flow)

```text
PlantUML: docs/architecture/diagrams/seq-intent-routing.puml
```

## Usage example

View the sequence diagram source:

```bash
sed -n '1,200p' docs/architecture/diagrams/seq-intent-routing.puml
```

## How to verify

Confirm the orchestration doc references the agent catalog:

```bash
rg -n "Agent Catalog" docs/architecture/agent-orchestration.md
```

Expected output: a link to `docs/agents/agent-catalog.md`.

## Implementation status

- **Implemented**: orchestration service manages agent lifecycle, dependency checks, policy enforcement,
  and Azure Service Bus-backed event distribution.

## Related docs

- [Agent Catalog](../agents/agent-catalog.md)
- [Security Architecture](security-architecture.md)
- [Connector Overview](../connectors/overview.md)
