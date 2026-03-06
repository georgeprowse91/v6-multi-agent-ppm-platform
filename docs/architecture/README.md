# Architecture

> Platform architecture reference for the multi-agent PPM system — covering system context, logical and physical design, AI and agent layers, data, connectors, security, observability, resilience, performance, tenancy, and all recorded architectural decisions.

## Contents

- [System Context](#system-context)
- [Logical Architecture](#logical-architecture)
- [Physical Architecture](#physical-architecture)
- [Deployment Architecture](#deployment-architecture)
- [AI Architecture](#ai-architecture)
- [Agent Orchestration](#agent-orchestration)
- [Agent Runtime](#agent-runtime)
- [Workflow Architecture](#workflow-architecture)
- [Connector Architecture](#connector-architecture)
- [Data Architecture](#data-architecture)
- [Data Model](#data-model)
- [State Management](#state-management)
- [Vector Store Design](#vector-store-design)
- [Security Overview](#security-overview)
- [Security Architecture](#security-architecture)
- [Security Testing](#security-testing)
- [Container Runtime and Identity Policy](#container-runtime-and-identity-policy)
- [Observability](#observability)
- [Resilience](#resilience)
- [LLM Resilience](#llm-resilience)
- [Performance](#performance)
- [Tenancy Architecture](#tenancy-architecture)
- [Human-in-the-Loop](#human-in-the-loop)
- [Feedback Architecture](#feedback-architecture)
- [Design Review Notes](#design-review-notes)
- [Architecture Decision Records](#architecture-decision-records)

## System Context

### Purpose

Describe who uses the Multi-Agent PPM Platform, the external systems it integrates with, and the high-level system boundary. This section anchors the logical and physical architecture in the real enterprise ecosystem.

### Architecture-level context

The platform sits between portfolio stakeholders (PMO, delivery leads, finance, resource managers) and enterprise systems of record (PPM, ERP, HR, CRM, collaboration). It provides a unified AI-assisted workflow while preserving those systems as sources of truth. The system context diagram at `docs/architecture/diagrams/c4-context.puml` captures the boundary and integrations.

### System boundary and actors

**Primary actors**
- Portfolio leaders and PMO staff using the web experience.
- Project and program managers collaborating with agents.
- Finance, resource, and compliance stakeholders reviewing gates and approvals.

**External systems**
- PPM/work management: Jira, Azure DevOps, Planview, Clarity PPM, Monday.com, Asana, Smartsheet, Microsoft Project Server.
- ERP/Finance: SAP, Workday, Oracle ERP Cloud, NetSuite.
- HR/Workforce: ADP, SAP SuccessFactors.
- GRC/Risk: RSA Archer, LogicGate, ServiceNow GRC.
- CRM: Salesforce.
- Identity: Azure AD / Okta.
- Collaboration: Slack, Microsoft Teams, Microsoft 365, SharePoint, Confluence, Google Drive, Google Calendar, Outlook, Zoom.
- Communications: Twilio, Azure Communication Services, Azure Notification Hubs.
- IoT: IoT device telemetry integrations.

**System boundary**

The platform orchestrates tasks and maintains a canonical data model. It does **not** replace upstream systems of record; connectors synchronize data bi-directionally based on policy.

### Diagram

```text
PlantUML: docs/architecture/diagrams/c4-context.puml
```

### Usage example

View the system context diagram source:

```bash
sed -n '1,160p' docs/architecture/diagrams/c4-context.puml
```

### How to verify

Confirm the diagram file exists:

```bash
ls docs/architecture/diagrams/c4-context.puml
```

Expected output: the PlantUML file path.

### Implementation status

- **Implemented**: documentation and diagram source.
- **Implemented**: connector registry includes the full set of documented external systems.

### Related docs

- Logical Architecture
- Connector Overview
- Agent Orchestration

---

## Logical Architecture

### Purpose

Explain how logical components (agents, orchestration, data services, and connectors) collaborate to deliver the Multi-Agent PPM Platform capabilities.

### Architecture-level context

The logical architecture organizes the platform into three logical planes:

1. **Engagement plane** (API gateway, web prototype) in `apps/`.
2. **Decision plane** (agent orchestration and domain agents) in `agents/`.
3. **Integration and data plane** (connectors, data schemas, lineage) in `connectors/` and `data/`.

These planes are orchestrated through intent routing, task planning, and policy enforcement. Each domain agent owns canonical data entities and publishes events consumed by other agents or analytics workflows.

### Key components

- **Intent Router**: classifies user intent and routes to domain agents.
- **Response Orchestrator**: builds multi-step plans and composes responses.
- **Domain agents (Agents 03–25)**: own specific PPM domain processes (see the [Agent Catalog](../../agents/AGENT_CATALOG.md)).
- **Connector runtime**: translates between canonical schemas and external APIs.
- **Data services**: enforce schema validation, lineage capture, and quality scoring.

### Diagrams

```text
PlantUML: docs/architecture/diagrams/c4-component.puml
```

Supplementary service interaction diagram:

```text
PlantUML: docs/architecture/diagrams/service-topology.puml
```

### Usage example

Inspect the component diagram source:

```bash
sed -n '1,200p' docs/architecture/diagrams/c4-component.puml
```

### How to verify

Check that this document references the agent catalog:

```bash
rg -n "Agent Catalog" docs/architecture/logical-architecture.md
```

Expected output: a reference to `agents/AGENT_CATALOG.md`.

### Implementation status

- **Implemented**: agent runtime scaffolding, API gateway, and orchestration service.
- **Implemented**: workflow engine integration and domain agent registrations in `services/agent-runtime/`.

### Related docs

- [Agent Catalog](../../agents/AGENT_CATALOG.md)
- Agent Orchestration
- Data Architecture

---

## Physical Architecture

### Purpose

Describe the physical deployment topology for the Multi-Agent PPM Platform, including compute tiers, storage, networking, and environment isolation.

### Architecture-level context

The platform is designed for Azure-friendly deployment with a hub-and-spoke network model, private endpoints for data services, and workload separation by environment (dev, staging, production). The physical topology maps logical services into Azure resources such as AKS, Azure Database for PostgreSQL, Redis, and Azure Service Bus.

### Physical topology (Azure reference)

- **Ingress and edge**: Azure Front Door → Application Gateway / WAF.
- **Compute**: AKS for agent services and API gateway; optional Azure Container Apps for connectors.
- **Data**: Azure Database for PostgreSQL (operational store), Azure Cache for Redis, Azure Blob Storage for documents.
- **Messaging**: Azure Service Bus for event propagation.
- **Secrets**: Azure Key Vault; managed identities for access.

### Diagram

```text
PlantUML: docs/architecture/diagrams/c4-container.puml
```

### Usage example

View the container diagram:

```bash
sed -n '1,200p' docs/architecture/diagrams/c4-container.puml
```

### How to verify

Confirm that the diagram file exists:

```bash
ls docs/architecture/diagrams/c4-container.puml
```

Expected output: the PlantUML file path.

### Implementation status

- **Implemented**: Azure infrastructure deployment scripts in `ops/infra/terraform` and `ops/infra/kubernetes`.

### Related docs

- Deployment Architecture
- [Infrastructure README](../../ops/infra/README.md)
- Security Architecture

---

## Deployment Architecture

### Purpose

Explain how the platform is deployed across environments, how releases move through the pipeline, and how disaster recovery (DR) is handled.

### Architecture-level context

The deployment architecture maps logical components into Azure environments with clear separation between dev, staging, and production. CI/CD uses GitHub Actions to build containers, run tests, and publish artifacts. Infrastructure-as-code lives under `ops/infra/`.

### Environment matrix

| Environment | Purpose | Data handling | Infra path |
| --- | --- | --- | --- |
| Dev | Engineer experimentation | Synthetic/seed data only | `ops/infra/terraform/envs/dev/` |
| Staging | Pre-prod validation | Sanitized data | `ops/infra/terraform/envs/stage/` |
| Production | Customer workloads | Live data with retention policies | `ops/infra/terraform/envs/prod/` |

### Release flow

1. **Build**: GitHub Actions builds Docker images from `apps/api-gateway/Dockerfile`.
2. **Validate**: unit tests and docs checks (`ops/scripts/check-links.py`, `ops/scripts/check-placeholders.py`).
3. **Deploy**: Terraform provisions infrastructure, then Kubernetes manifests roll out services.

### Diagram

```text
PlantUML: docs/architecture/diagrams/deployment-overview.puml
```

### DR strategy

- Active-passive failover in a paired Azure region with scripted region flips.
- RPO target: 15 minutes; RTO target: 2 hours.
- Backups stored in geo-redundant storage with quarterly restore drills.

### Usage example

Show Terraform environments:

```bash
ls ops/infra/terraform
```

### How to verify

Inspect the Kubernetes deployment manifest:

```bash
sed -n '1,160p' ops/infra/kubernetes/deployment.yaml
```

Expected output: deployment spec with container image and environment variables.

### Implementation status

- **Implemented**: CI pipeline, Dockerfiles, Terraform environment overlays, and DR failover scripts.

### Related docs

- Container Runtime Identity Policy
- Physical Architecture
- [Runbooks](../runbooks.md)
- [Infrastructure README](../../ops/infra/README.md)

---

## AI Architecture

### Purpose

Describe the LLM provider abstraction, prompt management, and safety controls implemented in the platform.

### Architecture-level context

AI capabilities are provided through a shared LLM client package and prompt registry. Agent runtimes call the LLM client via the Intent Router and other domain agents. Prompt templates are stored and versioned in the repository for traceability and offline testing.

### Core building blocks

| Capability | Implementation | Notes |
| --- | --- | --- |
| LLM provider abstraction | `packages/llm/src/llm/client.py` | Supports `mock`, `openai`, and `azure-openai` providers. |
| Prompt registry | `agents/runtime/prompts` | YAML prompt definitions validated against `prompt.schema.json`. |
| Redaction rules | `agents/runtime/agents/runtime/prompts/prompt_registry.py` | Redacts sensitive fields from prompt payloads. |
| Intent routing | `agents/core-orchestration/intent-router-agent` | Uses LLM responses to select agent plans. |

### Provider selection and configuration

- **Mock provider (default):** Uses `LLM_MOCK_RESPONSE` or `LLM_MOCK_RESPONSE_PATH` for deterministic outputs.
- **OpenAI provider:** Set `LLM_PROVIDER=openai` and configure `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`.
- **Azure OpenAI provider:** Set `LLM_PROVIDER=azure-openai` and configure `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`.

### Prompt management

Prompt YAML files include metadata and redaction rules. The prompt registry loads prompts by agent and purpose and validates them against the schema before use.

- Prompt examples: `agents/runtime/agents/runtime/prompts/examples/*.prompt.yaml`
- Schema validation: `agents/runtime/agents/runtime/prompts/schema/prompt.schema.json`

### Safety and guardrails

- **Redaction:** The prompt registry applies redaction rules to remove sensitive fields before sending data to LLM providers.
- **RBAC enforcement:** The API gateway and policy engine enforce permissions before agent execution.
- **Deterministic testing:** Mock responses enable reproducible runs in CI and local development.

### Verification steps

List available prompt definitions:
```bash
ls agents/runtime/agents/runtime/prompts/examples
```

Inspect the LLM provider selection logic:
```bash
rg -n "LLM_PROVIDER" packages/llm/src/llm/client.py
```

### Implementation status

- **Implemented:** LLM client abstraction, mock/OpenAI/Azure providers, prompt registry with schema validation.
- **Implemented:** Prompt version promotion workflows and registry CLI tooling in `packages/llm`.

### Related docs

- Agent Orchestration
- [LLM Package README](../../packages/llm/README.md)
- Security Architecture

---

## Agent Orchestration

### Purpose

Describe how the platform routes user intent, plans multi-step workflows, executes tool calls, and composes responses across the 25-agent ecosystem.

### Architecture-level context

Agent orchestration sits between the experience layer (`apps/`) and domain agents (`agents/`). It coordinates intent detection, guardrails, memory/state, connector access, and response composition. The catalog of agent responsibilities is defined in the [Agent Catalog](../../agents/AGENT_CATALOG.md).

### Orchestration flow

1. **Intent routing**: the Intent Router agent classifies the user request and selects candidate agents.
2. **Plan creation**: the Response Orchestration agent builds a multi-step plan and enforces policy guardrails.
3. **Tool execution**: domain agents invoke connectors and data services using canonical schemas.
4. **State management**: results are stored in short-term state (request context) and long-term knowledge (data/lineage).
5. **Response composition**: the Response Orchestration agent synthesizes a final response and cites source data.

### Guardrails and escalation

- **Policy guardrails**: RBAC/ABAC checks are performed before tool execution.
- **Safety gates**: approvals are required for high-impact actions such as budget changes and scope changes.
- **Escalation**: if confidence is low or data is missing, the Approval Workflow agent requests human input.

### Event bus

Agent coordination relies on an event bus abstraction that can publish and subscribe to orchestration topics. Production deployments use Azure Service Bus topics via the shared `packages/event-bus` package, which exposes an async API for publishing messages and listening on subscriptions. The in-memory bus remains available for local development and unit testing.

### Sequence diagram (example flow)

```text
PlantUML: docs/architecture/diagrams/seq-intent-routing.puml
```

### Usage example

View the sequence diagram source:

```bash
sed -n '1,200p' docs/architecture/diagrams/seq-intent-routing.puml
```

### How to verify

Confirm the orchestration document references the agent catalog:

```bash
rg -n "Agent Catalog" docs/architecture/agent-orchestration.md
```

Expected output: a link to `agents/AGENT_CATALOG.md`.

### Implementation status

- **Implemented**: orchestration service manages agent lifecycle, dependency checks, policy enforcement, and Azure Service Bus-backed event distribution.

### Related docs

- [Agent Catalog](../../agents/AGENT_CATALOG.md)
- Security Architecture
- Connector Overview

---

## Agent Runtime

### Purpose

Define the AgentRun lifecycle, orchestrator state transitions, and transparency surfaces that expose progress and auditability to product interfaces and operators. This section complements [Agent Orchestration](#agent-orchestration) and the runtime package overview in [Readme](../../agents/runtime/README.md).

### AgentRun lifecycle

Agent runs move through explicit, observable states that the orchestrator and UI can surface. The canonical lifecycle is:

- **queued**: A request has been accepted, persisted, and is waiting for orchestration resources.
- **running**: The orchestrator is actively dispatching work to one or more agents.
- **blocked**: Execution is paused pending input (human approval, missing data, or external dependency resolution).
- **completed**: The run finished successfully and emitted a final response.
- **failed**: The run terminated due to an error, timeout, or policy violation.

State transitions are recorded in the runtime audit log and published on the event bus so downstream services can render progress or trigger follow-up actions.

### Orchestrator interaction model

The orchestrator loop coordinates AgentRun transitions and publishes state changes through runtime hooks.

1. **Queue intake**: The runtime accepts a request, assigns an AgentRun ID, and sets the state to `queued`.
2. **Dispatch**: The orchestrator moves the run to `running`, selects agents per the orchestration plan, and invokes tool execution.
3. **Block handling**: If approvals, data dependencies, or guardrails prevent execution, the orchestrator emits a `blocked` transition and registers the blocking reason.
4. **Resolution**: Once blocking conditions clear, the orchestrator resumes and returns to `running`.
5. **Completion**: The orchestrator records either `completed` or `failed` and emits the final response payload.

Runtime hooks include audit logging, event bus publication, and state store updates so that orchestration transitions remain consistent across the runtime stack.

### Audit and event surfaces

Transparency relies on durable, queryable surfaces:

- **Audit log**: Each transition, tool call, and policy decision is written to the runtime audit facility (`agents/runtime/src/audit.py`) for compliance and troubleshooting.
- **Event bus**: The runtime publishes transition events to the event bus so downstream subscribers can react in near real time.
- **State store**: The state store persists AgentRun metadata, including the latest lifecycle state and blocking reason, for UI queries.

### UI surfaces

Product interfaces should surface AgentRun state and context to users:

- **Progress indicators**: Show queued, running, blocked, completed, and failed states with clear messaging and timestamps.
- **Explanations**: Provide human-readable summaries of why a run is blocked or failed, drawing from audit metadata.
- **Async notifications**: Deliver notifications when a blocked run resumes or completes to avoid requiring continuous polling.

### Runtime secret handling policy

Agent request and task handlers **must not** mutate process-global environment variables (e.g., `os.environ[...] = ...`). Runtime code should pass secrets through explicit inputs such as dependency-injected secret providers, per-agent context objects, or function parameters.

When integrating with legacy APIs that only accept environment variables, project secrets into a tightly scoped subprocess environment and avoid mutating the current process environment.

### Cost aggregation metadata

Agent runtime responses include `metadata.cost_summary` with:

- LLM tokens (`request`, `response`, `total`)
- External API cost totals (`api_cost_total_usd`)
- Cost by connector (`api_cost_by_connector`)

The orchestrator aggregates these values into run-level metrics under `OrchestrationResult.metrics.cost_summary` and persists the same summary in shared orchestration context.

### Related docs

- Agent Orchestration
- [Runtime README](../../agents/runtime/README.md)

---

## Workflow Architecture

### Purpose

Explain how durable workflows are defined, executed, and audited across the platform.

### Architecture-level context

Workflows are the backbone for stage-gate execution, approvals, and multi-step orchestration. The platform uses a dedicated workflow service (`apps/workflow-service`) and the Approval Workflow agent (`agents/core-orchestration/approval-workflow-agent`) to execute workflow instances, persist state in an external database, and emit audit entries to the audit log service. Orchestration services and agents call the workflow service to start, resume, and inspect workflow runs, while worker nodes pull tasks from a shared queue.

### Core components

| Component | Location | Responsibility |
| --- | --- | --- |
| Workflow engine API | `apps/workflow-service/src/main.py` | REST API for workflow lifecycle (start/status/resume). |
| Approval Workflow agent | `agents/core-orchestration/approval-workflow-agent/src/approval_workflow_agent.py` | Orchestrates workflow execution, approval chains, and task routing across worker nodes. |
| Workflow storage | `agents/core-orchestration/approval-workflow-agent/src/workflow_state_store.py` | External database-backed state store for workflow definitions, instances, and tasks. |
| Workflow task queue | `agents/core-orchestration/approval-workflow-agent/src/workflow_task_queue.py` | Queue-backed coordination for distributing workflow tasks to workers. |
| Workflow definitions | `apps/workflow-service/workflows/definitions/*.workflow.yaml` | Declarative workflow definitions. |
| Workflow registry | `apps/workflow-service/workflow_registry.py` | Discovery of workflow definitions. |
| Orchestration service | `apps/orchestration-service/src/main.py` | Calls workflow service and coordinates agent plans. |

### Workflow lifecycle

1. **Start**: Clients POST to `/v1/workflows/start` with a workflow ID and payload.
2. **Persist**: The workflow service stores a `run_id`, `workflow_id`, `tenant_id`, status, and payload in PostgreSQL (or another external database).
3. **Distribute**: Workflow tasks are enqueued to a shared message queue for worker nodes.
4. **Resume**: Orchestration services call `/v1/workflows/resume/{run_id}` or workers resume from persisted state after failures.
5. **Audit**: Workflow changes are emitted to the audit log for retention and compliance.

### Workflow definitions and fields

Workflow definitions live in `apps/workflow-service/workflows/definitions/*.workflow.yaml` and follow the schema below.

| Field | Description |
| --- | --- |
| `apiVersion` | Workflow API version (currently `ppm.workflows/v1`). |
| `kind` | Resource kind (`Workflow`). |
| `metadata.name` | Workflow identifier used by `/v1/workflows/start`. |
| `metadata.version` | Version string for the workflow. |
| `metadata.owner` | Owning service or agent. |
| `metadata.description` | Human-readable description. |
| `steps[].id` | Unique step identifier. |
| `steps[].type` | Step type (`task`, `decision`, `approval`, `notification`). |
| `steps[].next` | Next step ID (null ends the workflow). |
| `steps[].config` | Step-specific config (agent/action or channel/message). |
| `steps[].branches` | Decision branches with conditions and next steps. |
| `steps[].default_next` | Fallback next step for decisions. |
| `steps[].timeout_seconds` | Timeout window for approvals. |

### Available workflows

| Workflow | Purpose | Key steps |
| --- | --- | --- |
| `intake-triage` | Route new intake requests to the appropriate agent and notify owners. | `capture-intake` → `evaluate-risk` → `notify-owner` |
| `Publish Charter` | Draft and approve a project charter before publishing. | `draft_charter` → `approval_gate` → `publish_charter` |

### Failure handling and retries

- Workflows persist state in an external database, allowing the system to resume across nodes after process restarts.
- Retry policies are enforced by orchestration logic and workflow service status transitions.
- Worker failures are handled by marking tasks failed and leaving state in the database for retry or manual intervention.

### Operational guidance

- **State backend**: Set `WORKFLOW_DATABASE_URL` and `WORKFLOW_STATE_BACKEND=db` to enable PostgreSQL persistence.
- **Queue backend**: Set `WORKFLOW_QUEUE_BACKEND=rabbitmq` and `WORKFLOW_QUEUE_URL` to enable task distribution.
- **Tenant enforcement**: The workflow service enforces tenant ownership on reads and resumes.
- **Workflow updates**: Version workflow definitions as new YAML files and update registry usage in orchestration services.

### Verification steps

Inspect workflow definitions:
```bash
ls apps/workflow-service/workflows/definitions
```

Check workflow service routes:
```bash
rg -n "workflows" apps/workflow-service/src/main.py
```

Verify workflow instance storage includes `tenant_id`:
```bash
rg -n "tenant_id" apps/workflow-service/src/workflow_storage.py
```

### Implementation status

- **Implemented:** Workflow engine API, external database-backed storage, queue-driven task distribution, YAML workflow definitions.

### Related docs

- Agent Orchestration
- Deployment Architecture
- Quickstart Runbook

---

## Connector Architecture

### Introduction

The Multi-Agent PPM Platform acts as an orchestration layer over existing enterprise systems such as PPM tools, task trackers, ERPs, HRIS, procurement systems, and collaboration platforms. Integration is therefore a critical pillar of the architecture. This section outlines the guiding principles, architectural patterns, reusable components, and monitoring strategies that underpin the platform's integration capabilities.

### Integration principles

The architecture defines five principles for integration:

**Agents own integrations:** Each agent is responsible for reading from and writing to external systems within its domain. For example, the Financial Management agent integrates with SAP for budgets and actuals, while the Resource and Capacity agent integrates with Workday or SuccessFactors for employee data. This ownership ensures domain expertise resides in the agent and reduces cross-module dependencies.

**Bi-directional synchronization:** Integrations support two-way data flows where appropriate. Changes in the PPM platform are propagated back to systems of record (e.g., updating task status in Jira), and external updates are pulled into the platform. Conflict resolution strategies (e.g., last writer wins, authoritative source) are defined per data type.

**Event-driven updates:** Whenever possible, the platform uses event hooks or webhooks from external systems to receive near real-time updates. Agents publish events when internal data changes. This reduces polling and ensures timely synchronization.

**Eventual consistency:** While real-time updates are ideal, the architecture accepts eventual consistency to balance performance and reliability. Agents reconcile differences via scheduled synchronization jobs and implement idempotent operations.

**Graceful degradation:** Integration failures are inevitable. The system handles API outages, timeouts, and throttling by queuing updates, retrying with exponential backoff, and notifying administrators. Core functionality continues using cached data, with warnings to users when data may be stale.

### API gateway pattern

All external calls pass through an API gateway that centralizes cross-cutting concerns:

**Authentication and authorization:** Validates OAuth tokens or API keys and enforces permissions.

**Rate limiting:** Protects downstream systems from overload by limiting requests per user or tenant.

**Protocol translation:** Converts between GraphQL used internally and REST, SOAP, or OData used by external systems. Also handles JSON ↔ XML conversion when needed.

**Logging and monitoring:** Records request/response metadata and latency for analytics and debugging.

**Circuit breaking and retry:** Detects repeated failures and opens circuits to prevent cascading outages. Implements configurable retry policies.

**Schema validation:** Validates request and response payloads against schemas to catch errors early.

The gateway routes calls to connectors or directly to agents for internal API requests. By consolidating these functions, it reduces duplication and simplifies agent implementations.

### Connector library

To avoid duplicating integration logic, the platform provides a reusable connector library. Each connector is implemented as a microservice (or serverless function) that exposes a consistent API to agents and handles all interactions with a specific external system. Key features include:

**Authentication management:** Supports OAuth 2.0, SAML, Basic Auth, and API tokens. Secrets are stored in a secure vault and rotated automatically.

**Request and response mapping:** Transforms platform objects into the external system's API payloads and vice versa (e.g., mapping a Task to a Jira issue).

**Pagination and throttling:** Handles paging through large result sets and respects API rate limits. Implements backoff strategies.

**Error handling and retries:** Normalizes error responses, retries transient failures, and surfaces meaningful errors to calling agents.

**Schema validation and versioning:** Validates payloads against API schemas and manages version differences to support backward compatibility.

**Bi-directional sync helpers:** Provides utilities to determine whether an update originated from the platform or the external system, preventing update loops. Implements conflict resolution strategies.

### Integration patterns by domain

Each domain agent follows specific integration patterns based on its responsibilities. Examples include:

#### Financial Management agent

**ERP integration (SAP, Oracle, Workday):** Retrieve budgets, actual costs, and forecasts via REST or OData APIs. Push budget adjustments and payment approvals back to ERP. Use scheduled batch jobs for large data extracts and event-based updates for critical changes.

**Multi-currency handling:** Convert currencies using exchange rate feeds. Sync exchange rates daily.

**Period close support:** During month-end close, lock financial periods and require manual approval before posting adjustments.

#### Resource and Capacity agent

**HRIS integration (Workday, SuccessFactors):** Pull employee profiles, skills, availability, and cost rates. Push project allocations and timesheet entries if the HR system supports it. Use delta queries to reduce data volume.

**Calendar and directory integration:** Sync with calendar systems (Outlook, Google Calendar) to create meetings for resource assignments and with directories (Azure AD) to resolve user identities.

#### Schedule and Planning agent

**Task trackers (Jira, Azure DevOps, Monday.com):** Map platform tasks to issues or user stories. Support creation, update, and status sync. Use webhooks for updates from task trackers and periodic reconciliation jobs.

**PM tools (Microsoft Project, Smartsheet):** Import/export schedules via file formats (e.g., `.mpp`) or APIs. Convert Gantt charts into the platform's timeline representation.

#### Vendor and Procurement agent

**Procurement systems (Coupa, Ariba):** Sync purchase requisitions, purchase orders, invoices, and vendor onboarding data. Implement approvals in the platform and propagate decisions to procurement systems.

**Vendor risk services:** Integrate with third-party services to perform vendor risk assessments and compliance checks (e.g., Dun & Bradstreet, LexisNexis).

#### Communications and collaboration

**Messaging platforms (Slack, Microsoft Teams):** Post updates, alerts, and meeting summaries. Support interactive bots that allow users to approve requests or update tasks directly from chat.

**Email and calendar:** Send notifications, meeting invites, and agenda documents. Integrate with Exchange/Outlook and Google Workspace.

These patterns serve as blueprints; each connector encapsulates the specific API calls, data mappings, and scheduling needs.

### Monitoring and metrics

Integration reliability is measured through metrics and dashboards. Key metrics include:

**Sync success rate:** The percentage of successful synchronization operations vs. total attempts. Target: >99%.

**Latency and throughput:** Time taken to complete API calls and number of calls per minute. Monitored to detect slowdowns or bottlenecks.

**Queue backlog:** Number of pending events or messages waiting for processing. High backlog triggers scaling or investigation.

**Error rate and types:** Frequency and classification of errors (e.g., authentication failure, rate limit exceeded). Helps prioritize fixes.

**Data freshness:** Age of data since last successful sync. Alerts when exceeding configured thresholds.

Dashboards in tools such as Grafana or Power BI visualize these metrics. Alerts notify integration teams of anomalies, and logs capture detailed information for troubleshooting.

---

## Data Architecture

### Purpose

Describe how canonical PPM data is stored, validated, synchronized, and audited across the platform.

### Architecture-level context

Data architecture ties together canonical schemas (`data/schemas/`), quality rules (`data/quality/`), lineage artifacts (`data/lineage/`), and the services that store and query the data. It enables agents and connectors to share a consistent view of portfolios, programs, projects, and work items.

### Storage layers

- **Operational store**: PostgreSQL for canonical entities.
- **Cache**: Redis for fast reads of frequently accessed data.
- **Document storage**: Blob storage for charters, contracts, and evidence files.
- **Event stream**: Service Bus for domain events and sync notifications.

### Persistence responsibilities

The platform exposes multiple storage backends so services can pick the store that matches the data shape and access pattern. The matrix below summarizes how current services use each backend and where to look in the codebase for implementation details.

| Backend | Primary responsibility | Current usage in services |
| --- | --- | --- |
| PostgreSQL | Canonical, relational PPM entities that need schema validation, joins, and strong consistency. | Data service persists schema registry and canonical entities via its SQL store; orchestration state is configured to use Postgres for durability in production. |
| Cosmos DB | Flexible document storage for semi-structured records and large JSON payloads that benefit from partitioning by tenant or document type. | Integration persistence provides a Cosmos-backed document store (`CosmosDocumentStore`) that can be wired into services needing document-style storage. |
| Redis | Low-latency cache and transient state to avoid repeated queries against operational stores. | Cache provider in integration persistence supports Redis for shared caching and can be paired with cache-aside workflows. |

### Data flow patterns

- **Connector sync** updates canonical records and emits lineage.
- **Agent writes** validate against schemas and publish domain events.
- **Analytics pipeline** consumes events for reporting via the analytics service and KPI scheduler.

### Diagram

```text
PlantUML: docs/architecture/diagrams/data-lineage.puml
```

### Usage example

Inspect the canonical project schema:

```bash
sed -n '1,80p' data/schemas/project.schema.json
```

### How to verify

Confirm lineage artifacts are present:

```bash
ls data/lineage
```

Expected output: `example-lineage.json` and `README.md`.

### Implementation status

- **Implemented**: canonical schemas, lineage artifacts, quality rules, analytics service, and data-lineage service.
- **In progress**: expanded automated lineage generation across all connectors and analytics warehouse exports.

### Related docs

- Data Model
- Data Quality
- Data Lineage

---

## Data Model

### Purpose

Define canonical propagation rules, conflict handling, and scenario guidance beyond the entity list documented in the canonical data model reference.

### Canonical entities and ownership

Canonical entities and primary owners are maintained in the Canonical Data Model. The Data Service (`services/data-service/`) stores and serves canonical entities and schema versions.

### Propagation rules (WBS → Schedule → Risk/Budget)

- **Canonical ownership first:** The owning agent or service is the source of truth for its entity; downstream systems consume canonical records rather than rewriting them.
- **Directional propagation:** Work breakdown structure (WBS) changes flow into schedule work items, which then inform downstream risk and budget entities.
- **Mode-aware application:**
  - **merge:** update only fields present in the incoming payload, preserving existing canonical values.
  - **replace:** overwrite the canonical payload with the incoming payload.
  - **enrich:** append non-null fields without overwriting existing canonical values.
- **Field-level constraints:** Only mapped target fields propagate; unmapped fields are ignored to prevent schema drift.
- **Lineage requirements:** Each propagation emits lineage metadata with source system, entity, transformation, and timestamp.

### Conflict handling and audit expectations

- **Conflict policy:**
  - **source_of_truth:** accept updates from the declared owner system.
  - **last_write_wins:** prefer the most recent `updated_at` timestamp.
  - **manual_required:** record conflicts when ownership is ambiguous or an approval gate is configured.
- **Audit trail:** Conflicts and resolution strategies must be logged with source, target, timestamps, and applied policy.
- **Review workflow:** Manual conflicts remain in a review queue until resolved and re-propagated.

### Scenario modeling (baseline vs. variants)

- **Baseline scenario:** The baseline captures the approved plan for schedule, risk, and budget. Canonical entities represent the baseline unless a scenario tag indicates otherwise.
- **Variant scenarios:** Variants inherit from the baseline and override only the changed entities. Variants must retain a pointer to the baseline identifier for traceability.
- **Propagation scope:**
  - Baseline updates cascade to variants only when explicitly rebaselined.
  - Variant updates never overwrite baseline records; they propagate only within the same scenario context.

### Canonical storage context

Canonical entities and schema versions are stored and served by the Data Service. See the [Data Service README](../../services/data-service/README.md) for implementation details.

---

## State Management

### Overview

The platform uses a **unified memory service** to persist and retrieve shared context between agents and orchestrator task executions. This reduces ad-hoc context passing and improves state consistency.

### Memory lifecycle

1. The orchestrator resolves a memory key (typically a correlation or conversation ID).
2. Existing context is loaded from memory before task execution.
3. Each agent task reads merged context and dependency outputs.
4. After task completion, the orchestrator appends history, outputs, and insights, then persists context.
5. Base agents can also save and load per-agent scoped context using `conversation_id:agent_id` keys.

### Retrieval hygiene

- Context is namespaced by memory key to avoid accidental cross-conversation leakage.
- Agent-local entries use conversation and agent identifiers.
- The orchestrator normalizes insights and keeps task output lineage in `agent_outputs`.
- TTL can be configured to evict stale context and avoid context pollution.

### Privacy and data handling

- Store only operationally necessary context.
- Avoid saving raw secrets or PII unless required by policy.
- Use TTL for temporary conversation state to reduce retention duration.
- Prefer sanitized summaries over full payloads for long-term persistence.

### Components

- `services/memory_service/memory_service.py`: in-memory and SQLite memory backend with optional TTL.
- `packages/memory_client.py`: client wrapper used by orchestrator and agents.
- `agents/runtime/src/base_agent.py`: memory helper methods (`save_context`, `load_context`).
- `agents/runtime/src/orchestrator.py`: centralized context persistence during DAG execution.

---

## Vector Store Design

### Overview

The platform supports a shard-aware FAISS-backed vector store implementation for high-volume duplicate detection and semantic retrieval workflows. The implementation centers on `FaissVectorStore` in `packages/vector_store/faiss_store.py` and a higher-level adapter `FaissBackedVectorSearchIndex` used by portfolio agents.

### Architecture

- **Storage primitive**: `FaissVectorStore`.
  - Supports configurable sharding (`num_shards`) to spread vectors across partitions.
  - Uses `IndexIVFFlat` when `faiss` is available; otherwise falls back to a NumPy cosine similarity path.
  - Exposes `add_embeddings`, `search`, `search_many`, `delete`, and `flush`.
- **Agent integration adapter**: `FaissBackedVectorSearchIndex` in `agents/common/integration_services.py`.
  - Preserves the existing `add` and `search` style used by agents.
  - Loads index tuning from `ops/ops/config/vector_store.yaml`.
  - Stores metadata separately and merges metadata into search results.

### Scalability controls

#### Sharding

- Each document ID is deterministically mapped to a shard.
- Search fans out across shards and merges top results.
- Recommended scale-up path:
  1. Increase `num_shards`.
  2. Increase `nlist`.
  3. Tune `nprobe` to balance recall vs. latency.

#### Batching

- `add_embeddings` stages vectors in per-shard queues.
- Flush occurs automatically at `batch_size` and can be forced via `flush()`.
- `search_many` provides multi-query batch execution.

#### Caching

- Internal LRU-style cache stores recent query results with TTL (`cache_ttl_seconds`) and bounded size (`cache_size`).
- The agent adapter also keeps a small query cache (`query_cache_size`) to avoid recomputation of repeated queries.

#### TTL-based retention

- Embeddings can be configured with `embedding_ttl_seconds`.
- Expired vectors are purged during add/search operations.
- Use shorter TTL for high-churn domains and longer TTL for historical benchmarking workloads.

### Operational tuning

Configure index settings in `ops/ops/config/vector_store.yaml`:

- `num_shards`: parallelism and index partitioning.
- `nlist`: coarse cluster count for IVF.
- `nprobe`: cluster probes per query.
- `batch_size`: write throughput vs. index freshness.
- `cache_size` and `cache_ttl_seconds`: query cache behavior.
- `embedding_ttl_seconds`: lifecycle cleanup window.

### Current agent usage

- Demand and Intake agent (`demand-intake-agent`) uses the `demand_intake` index profile.
- Business Case and Investment agent (`business-case-agent`) uses the `business_case` index profile.

## Security Overview

The platform protects data, enforces access controls, captures audit evidence, and satisfies compliance requirements across four intersecting planes: identity (SSO), authorization (RBAC/ABAC), data protection (encryption and retention), and audit/monitoring. Security controls are documented under `docs/compliance/` and enforced by agents and infrastructure defined in `ops/infra/`.

### Identity and authentication

- **SSO**: Azure AD / Okta via OIDC or SAML.
- **Service authentication**: managed identities or mTLS between internal services.
- **API tokens**: scoped tokens for external integrations.

### Authorization model (RBAC + ABAC)

- **RBAC**: role-based permissions for portfolios, programs, and projects.
- **ABAC**: attribute-based policies scoped to data classification, region, and business unit.
- **Field-level controls**: sensitive fields are masked for restricted roles.

### Audit events

Audit events are captured for:

- Stage-gate approvals
- Budget or scope changes
- Data synchronization activity
- Authentication and authorization decisions

The audit event schema is defined in [Audit Event.schema](../../data/schemas/audit-event.schema.json).

### Data protection and retention

- **Encryption**: TLS in transit; AES-256 at rest.
- **Secrets**: Azure Key Vault references held in `ops/config/`.
- **Retention**: see the Retention Policy for standard schedules.
- **Privacy**: a DPIA template is provided in the Privacy DPIA Template.

### Threat model summary

The Threat Model identifies the top platform risks:

- Connector credential leakage
- Unauthorized cross-tenant access
- LLM prompt injection
- Data exfiltration via integrations

Mitigations include secret rotation, tenant isolation, policy guardrails, and audit logging.

### Verification

To confirm compliance documents are present, run:

```bash
ls docs/compliance
```

Expected output includes `retention-policy.md` and `threat-model.md`.

To inspect the audit event schema:

```bash
sed -n '1,120p' data/schemas/audit-event.schema.json
```

### Implementation status

- **Implemented**: documentation, audit schema, retention and DPIA templates.
- **Implemented**: IAM role mapping with Azure AD group ingestion and automated policy enforcement via the policy engine.

### Related documentation

- Compliance Controls Mapping
- Financial Services Compliance Management Template (Australia)
- Retention Policy
- Threat Model

---

## Security Architecture

### Prompt injection detection and sanitisation

The runtime applies prompt injection checks to inbound user-authored prompt fields before agent processing.

#### Detection rules

`packages/llm/prompt_sanitizer.py` implements heuristic pattern checks for common attacks, including:

- attempts to ignore or override system/developer instructions,
- attempts to reveal secrets, credentials, hidden prompts, or chain-of-thought,
- role-escalation language (for example, pretending to be an admin),
- obfuscation hints around decoding hidden prompt material.

`detect_injection(prompt: str) -> bool` returns `True` if any of these patterns match.

#### Sanitisation rules

`sanitize_prompt(prompt: str) -> str` neutralises known attack phrases and high-risk formatting patterns by:

- replacing known injection phrases with `[REMOVED_INJECTION_PHRASE]`,
- neutralising triple-backtick blocks,
- HTML-encoding angle brackets.

#### BaseAgent enforcement flow

`agents/runtime/src/base_agent.py` evaluates candidate prompt fields during `execute()`.

- If injection is detected and `allow_injection: false` (default), execution is rejected with a safe user-facing error.
- If injection is detected and `allow_injection: true`, the prompt is sanitised and processing continues.
- Audit and structured logs include detection metadata: detected fields, sanitised fields, and enforcement mode.

#### Configuration

Per-agent behaviour is configurable in agent YAML files (for example `ops/config/agents/intent-router.yaml`):

```yaml
allow_injection: false
prompt_fields:
  - prompt
  - user_prompt
  - query
```

- `allow_injection` controls reject (`false`) vs sanitise-and-continue (`true`).
- `prompt_fields` defines which input keys are inspected.

---

## Security Testing

Automated static analysis and dynamic application security testing (DAST) are integrated into CI to detect vulnerabilities early.

### Tools integrated

- **Bandit**: Python static code analysis with security-focused rules.
- **OWASP ZAP baseline**: DAST against local application endpoints.

### Local execution

#### 1. Run static analysis (Bandit)

```bash
python ops/tools/run_bandit.py
```

Behaviour:

- Runs `bandit -r .` in JSON mode.
- Writes the report to `artifacts/security/bandit-report.json`.
- Exits non-zero if any **high severity** issues are found.

#### 2. Run DAST scan (OWASP ZAP baseline)

```bash
python ops/tools/run_dast.py
```

Behaviour:

- Starts a minimal built-in test app by default (or uses `--base-url` / `--app-cmd`).
- Verifies test endpoints (`/api`, `/health`) are reachable.
- Executes the ZAP baseline and stores reports in:
  - `artifacts/security/dast-report.json`
  - `artifacts/security/dast-report.html`
- Exits non-zero if any **high** or **critical** findings are detected.

Useful options:

```bash
python ops/tools/run_dast.py --base-url http://127.0.0.1:8000
python ops/tools/run_dast.py --app-cmd "uvicorn apps.api.main:app --host 127.0.0.1 --port 18080"
python ops/tools/run_dast.py --report-dir artifacts/security
```

### CI integration

The CI workflow (`.github/workflows/ci.yml`) executes both scripts and uploads generated reports as build artifacts under `security-scan-reports`.

### Interpreting reports

- **Bandit report** (`bandit-report.json`): inspect `results` for issue metadata and source locations.
- **DAST report** (`dast-report.json` / `dast-report.html`): inspect ZAP alerts. The script fails for:
  - `riskcode >= 3` (high), or
  - alerts labeled critical.

A failing security stage must be treated as a release blocker until findings are triaged and resolved or explicitly risk-accepted.

---

## Container Runtime and Identity Policy

### Monorepo-wide baseline

All first-party runtime containers in this monorepo must run as the same non-root Linux identity:

| Attribute | Value |
|-----------|-------|
| User | `appuser` |
| UID | `10001` |
| Group | `appuser` |
| GID | `10001` |

This baseline applies to services, apps, agents, and connector images unless an explicit exception is documented in this section.

### Security rationale

- Avoids privileged `root` execution at runtime.
- Provides a predictable least-privilege identity for Kubernetes/OpenShift and Docker runtimes.
- Reduces host bind-mount permission drift by keeping file ownership numerically consistent.
- Makes `COPY --chown` behaviour deterministic across images.

### Shared volumes and file ownership

To keep shared volume behaviour consistent across services:

1. Build images so application files are owned by `10001:10001`.
2. Run processes as UID/GID `10001:10001`.
3. For writable shared volumes, ensure the volume path is writable by `10001` (for example via storage class permissions, init jobs, or platform-level `fsGroup: 10001`).

Recommended Kubernetes `securityContext` alignment:

```yaml
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
fsGroup: 10001
allowPrivilegeEscalation: false
```

### Exceptions process

No current exceptions are required in-repo.

If a service must diverge (for example, requiring root to bind privileged ports, perform package installation at runtime, or accommodate third-party image constraints), the exception must be documented in this section with:

- service/image path,
- required UID/GID,
- specific security rationale,
- compensating controls,
- planned removal/review date.

## Observability

Observability spans the API gateway, orchestration runtime, and connector layer. Telemetry feeds the System Health agent and the Continuous Improvement agent so they can detect degradations and drive improvements.

### Telemetry standards

- **Logs**: structured logs exported via OpenTelemetry and correlated with trace context.
- **Metrics**: request latency, error rates, throughput, connector sync duration/success, per-agent execution duration, retries, and execution cost.
- **Traces**: end-to-end spans across request routing, orchestration, and connector sync operations.

#### Log schema (example)

```json
{
  "timestamp": "2026-01-15T14:30:00Z",
  "service": "agent-orchestrator",
  "trace_id": "trace-123",
  "level": "INFO",
  "message": "Plan executed",
  "context": {"intent": "create_project"}
}
```

### Correlation IDs and cost telemetry

Every top-level user request receives a `correlation_id` (UUID) that propagates through orchestrator context and downstream agent calls. Structured logs, audit events, and metrics include `correlation_id` so one query can be traced end-to-end across all participating agents.

Agent metrics include:

- `agent_execution_duration_seconds` histogram tagged with `agent_id`, `task_id`, and `correlation_id`.
- `agent_retries_total` counter tagged by the same dimensions.
- `agent_errors_total` counter tagged by the same dimensions.
- Cost counters (`external_api_cost`, `llm_tokens_consumed`) tagged with `correlation_id` for request-level attribution.

### SLO/SLI targets

| SLI | Target | Notes |
| --- | --- | --- |
| API availability | 99.9% monthly | Measured at API gateway |
| p95 orchestration response time | < 2.0s | Excludes long-running syncs |
| Connector sync success | 99% | Per connector, per day |
| Error budget | 0.1% | Tied to availability |

### Telemetry stack

#### Instrumentation

- The **API gateway** and **orchestration service** initialize OpenTelemetry tracing, metrics, and logging at startup.
- **Connectors** initialize OpenTelemetry via the connector SDK runtime to emit sync spans, duration metrics, record counts, and error counters.

#### Collection and export

The OpenTelemetry Collector receives OTLP data and exports to:

- **Metrics** → Prometheus (scrape the collector endpoint on `:8889`).
- **Traces** → Jaeger.
- **Logs** → Loki (Grafana log explorer), plus Azure Monitor for long-term retention.

Collector endpoints are configured via `JAEGER_COLLECTOR_ENDPOINT` and `LOKI_ENDPOINT` (see the telemetry service Helm values).

### Dashboards

Grafana dashboards are stored as JSON exports under `ops/infra/observability/dashboards`:

- `ppm-platform.json` — latency, throughput, error rate, and connector sync duration.
- `ppm-slo.json` — SLO adherence, connector sync success, and error budget tracking.
- `multi_agent_tracing.json` — correlation-based multi-agent views, retries/errors overlays, and cost breakdowns by agent.

![PPM platform dashboard](images/grafana-ppm-platform.svg)
![PPM SLO dashboard](images/grafana-ppm-slo.svg)

### Alerts

Alert rules aligned to SLOs/SLIs are defined in `ops/infra/observability/alerts/ppm-alerts.yaml` and cover:

- API gateway latency and error-rate breaches.
- Workflow and orchestration failure rates.
- Connector sync error rate and high latency.

Observability runbooks are located under `docs/runbooks/`.

---

## Resilience

Resilience covers agent orchestration, connector sync, data availability, and AI model dependencies. These patterns inform runbooks in `docs/runbooks/` and the System Health agent's alerting policies.

### Failure modes and mitigations

| Failure mode | Mitigation | Owner |
| --- | --- | --- |
| Connector API outage | Circuit breakers open after repeated failures; fallback response returned | API Gateway |
| LLM service degradation | Use cached responses; require human approval | Orchestrator |
| Data store failure | Scheduled backups and restore procedures; read-only mode | Platform Ops |
| Queue backlog | Shed non-critical jobs; prioritize gates | Workflow Service |

### LLM degradation modes

- **Degraded**: disable optional agent calls, return summaries.
- **Read-only**: prevent writes and require manual approvals.
- **Offline**: pause orchestration and rely on runbooks.

### Active-passive failover

The API gateway and orchestration service run two replicas in Kubernetes with active-passive semantics. A ConfigMap-backed leader election loop assigns one pod as the active leader, while the passive replica remains a hot standby. Readiness probes point to leader-aware endpoints so only the active pod receives traffic.

- **Leader election**: ConfigMap lock (`*-leader`) updated by the service pods.
- **Failover**: if the leader stops renewing, the passive pod acquires the lock and becomes active.
- **Probe behaviour**: passive pods return non-ready status to keep them out of service endpoints.

### Circuit breakers

Connector interactions are protected by an in-memory circuit breaker in the API gateway. Repeated connector failures open the circuit for the configured recovery window, returning a fallback response until a successful probe closes the circuit again.

- **Failure threshold**: 3 consecutive failures (configurable).
- **Recovery timeout**: 60 seconds (configurable).
- **Fallback**: `circuit_open` response for connector tests and webhooks.

### DR and backup strategy

PostgreSQL and Redis backups run as Kubernetes CronJobs with encrypted object storage uploads (see `ops/infra/kubernetes/manifests/backup-jobs.yaml`). The jobs create an on-demand dump and push it to a secured bucket using credentials stored in Kubernetes Secrets (`postgres-credentials`, `redis-credentials`, `backup-credentials`).

| Store | Schedule (UTC) | CronJob | Storage |
| --- | --- | --- | --- |
| PostgreSQL | 02:00 daily | `postgres-backup` | S3-compatible bucket with server-side encryption |
| Redis | 03:00 daily | `redis-backup` | S3-compatible bucket with server-side encryption |

#### Restore procedure

1. **Fetch backup artifacts** from the secure bucket (e.g., `s3://<bucket>/<prefix>/postgres/<date>/ppm-platform.dump` and `s3://<bucket>/<prefix>/redis/<date>/redis.rdb`).
2. **Restore PostgreSQL** with `pg_restore --clean --dbname=<db> ppm-platform.dump`.
3. **Restore Redis** by stopping Redis, replacing the `dump.rdb` file, and restarting the service.
4. **Validate** application connectivity and run smoke tests from the deployment runbook.

### Implementation status

Active-passive failover, circuit breakers, and scheduled backups are fully implemented.

---

## LLM Resilience

All LLM calls flow through `packages/llm/src/llm/client.py` (`LLMGateway`), which wraps provider-specific clients with layered resilience: timeouts, retries, circuit breakers, and provider-chain fallback.

### Timeout budget

| Layer | Default | Env var | Source |
| --- | --- | --- | --- |
| HTTP request timeout | 10 s | `LLM_TIMEOUT` | `packages/llm/src/llm/client.py` |
| Azure OpenAI provider | 10 s | `LLM_TIMEOUT` | `packages/llm/src/providers/azure_openai_provider.py` |

The `LLM_TIMEOUT` environment variable controls the per-request HTTP timeout for all LLM providers. In production, consider raising this to 30–60 s for complex multi-agent orchestration chains.

### Retry policy

Configured per provider via `ResilienceMiddleware`:

| Parameter | Default | Override |
| --- | --- | --- |
| Max attempts | 3 | Config dict `retry_policy.max_attempts` |
| Initial backoff | 0.2 s | Config dict `retry_policy.initial_backoff_s` |
| Backoff multiplier | 2.0× | Hardcoded in `RetryPolicy` |

Retryable HTTP status codes: `408, 409, 425, 429, 500, 502, 503, 504`.

Non-retryable errors (e.g., 401 auth failures) break the retry chain immediately.

### Circuit breaker

Configured in `packages/common/src/common/resilience.py`:

| Parameter | Default |
| --- | --- |
| Failure threshold | 5 failures within window |
| Failure window | 60 s |
| Recovery timeout | 30 s |

**State machine:**

1. **Closed** (normal) — requests pass through; failures are counted.
2. **Open** — after 5 failures within 60 s, all requests are rejected immediately with `CircuitOpenError` for 30 s.
3. **Half-open** — after 30 s, one probe request is allowed. If it succeeds the circuit closes; if it fails the circuit reopens.

State transitions emit the `circuit_breaker_state_transitions_total` Prometheus metric.

### Provider chain fallback

`LLMGateway` supports a provider chain (e.g., `["azure", "openai"]`). On retryable errors the gateway falls through to the next provider in the chain. Each provider maintains its own circuit breaker instance.

### Structured response retry

For JSON-structured responses (`structured()` method), the gateway applies up to 2 correction attempts. If the LLM returns invalid JSON, the gateway sends a correction prompt and retries parsing.

### Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_TIMEOUT` | `10` | HTTP request timeout in seconds |
| `LLM_PROVIDER` | `mock` | Provider name or comma-separated chain |
| `LLM_TEMPERATURE` | `0` | Model temperature (0 = deterministic) |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI API endpoint URL |
| `AZURE_OPENAI_API_KEY` | — | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | — | Azure OpenAI deployment/model name |
| `AZURE_OPENAI_API_VERSION` | — | Azure OpenAI API version |

### Production tuning recommendations

1. **Increase `LLM_TIMEOUT`** to 30–60 s for agent chains that involve multiple sequential LLM calls (e.g., intent routing → response orchestration → approval).
2. **Monitor circuit breaker state** via the `circuit_breaker_state_transitions_total` Prometheus metric. Alert on repeated open transitions.
3. **Set `LLM_PROVIDER`** to a real provider (e.g., `azure`) — the default `mock` provider is for development and testing only.
4. **Use provider chains** for high availability (e.g., `azure,openai`) so that transient failures on one provider fall through to the backup.

---

## Performance

Performance tuning spans the API gateway, agent orchestration, connector sync schedules, and data storage. Performance targets inform infrastructure sizing in `ops/infra/` and SLOs documented in the SLO/SLI runbook.

### Performance targets

| Area | Target |
| --- | --- |
| API p95 latency | < 2.0s |
| Agent plan creation | < 1.0s |
| Connector sync window | < 30 min per connector |
| Batch ingestion | 5k work items/min |

### Optimization strategies

- **Caching**: use Redis for frequently accessed portfolios and user profiles.
- **Async orchestration**: long-running tasks are delegated to workflows.
- **Connector throttling**: obey vendor rate limits and stagger syncs.
- **Data partitioning**: partition project data by tenant and time.
- **Analytics stack**: leverage Azure Synapse SQL/Spark pools, Data Factory pipelines, and Event Hub streaming to keep analytics workloads off the request path.

### Analytics performance stack

The analytics platform relies on Azure Synapse Analytics (dedicated SQL pools and Spark pools), Data Lake Gen2, Data Factory pipelines, Event Hub streaming, and Power BI Embedded to ensure dashboards remain responsive while heavy ETL and ML training workloads run asynchronously. Data flows from Planview, Jira, Workday, and SAP into Synapse via Data Factory, with real-time event ingestion through Event Hub and Azure Stream Analytics before reporting via Power BI and narrative services.

### Performance test harness

The primary performance harness lives under `tests/load/` and executes SLA-driven load scenarios against staging or production deployments. Targets and thresholds are captured in `tests/load/sla_targets.json`. The harness:

- Issues concurrent HTTP requests to the configured endpoints.
- Calculates average latency, p95 latency, error rate, and throughput.
- Fails CI when any SLA threshold is violated.

The harness defaults to the staging API gateway but supports overrides for alternate environments and auth headers via environment variables (see `tests/load/README.md`).

### Interpreting results

Each load scenario produces:

- **Average latency**: mean response time across the request set.
- **P95 latency**: tail latency for the slowest 5% of requests.
- **Error rate**: proportion of HTTP responses with status >= 400 or network failures.
- **Throughput**: requests per second achieved during the scenario.

Use the `LOAD_PROFILE` environment variable to select SLA thresholds for `ci`, `staging`, or `production`.

### Viewing latency and error metrics

Use the Grafana dashboards exported under `ops/infra/observability/dashboards`:

- `ppm-platform.json` — latency, throughput, and error rates across services.
- `ppm-slo.json` — SLO compliance and error budget burn.

Logs and traces are available via Loki and Jaeger as described in the Observability Architecture.

### Implementation status

The SLA-based load harness targeting staging/production, CI gating on SLA violations, documented targets, and observability dashboards are all fully implemented.

## Tenancy Architecture

### Purpose

Define the multi-tenancy model, tenant isolation boundaries, and configuration flows for the Multi-Agent PPM Platform.

### Architecture-level context

Tenant-aware routing is enforced at the API gateway and service layers. Each request includes a tenant identifier and is validated against configured identity and RBAC policies. Tenant configuration assets live under `ops/config/tenants/`, while authorization policies and data classification rules live under `ops/config/rbac/` and `ops/config/data-classification/`.

### Tenant identification and request flow

- **Headers:** Every request to a tenant-aware service must include `X-Tenant-ID`. The API gateway middleware validates the tenant claim in the JWT and rejects mismatches (`apps/api-gateway/src/api/middleware/security.py`).
- **Identity validation:** The gateway can validate JWTs locally using `IDENTITY_JWKS_URL` / `IDENTITY_JWT_SECRET` or delegate to the Identity Access service (`services/identity-access`).
- **Dev mode:** Local development can use `AUTH_DEV_MODE=true` with `AUTH_DEV_TENANT_ID` and `AUTH_DEV_ROLES` for deterministic testing.

### Data isolation approach

- **Logical isolation:** Tenant identifiers are persisted with records in workflow, analytics, audit, and document stores (`apps/workflow-service/src/workflow_storage.py`, `apps/analytics-service/src/scheduler.py`, `services/audit-log/src/main.py`, `apps/document-service/src/main.py`).
- **Authorization enforcement:** RBAC and classification-based checks occur in the gateway (field masking and permission checks) and the policy engine (`services/policy-engine`).
- **Storage boundaries:** The default local stores use SQLite files scoped by service; for production deployments, replace local storage with environment-specific backing stores via Helm/Terraform configuration.

### Tenant configuration assets

| Asset | Path | Purpose |
| --- | --- | --- |
| Tenant defaults | `ops/config/tenants/default.yaml` | Identity issuer, JWKS URL, and tenant metadata |
| RBAC roles/permissions | `ops/config/rbac/roles.yaml`, `ops/config/rbac/permissions.yaml` | Roles and permissions used by middleware and policy engine |
| Field-level rules | `ops/config/rbac/field-level.yaml` | Classification and field masking rules |
| Data classification | `ops/config/data-classification/levels.yaml` | Classification levels and retention policy bindings |

### Operational guidance

1. Create a tenant configuration file under `ops/config/tenants/` for each deployment.
2. Configure identity settings in environment variables or tenant config (issuer, JWKS URL, audience).
3. Validate RBAC/field-level rules before onboarding users.
4. Ensure Helm chart values define per-environment secret references (Key Vault or other secret stores).

### Verification steps

- Inspect the tenant config:
  ```bash
  sed -n '1,120p' ops/config/tenants/default.yaml
  ```
- Confirm API gateway tenant enforcement:
  ```bash
  rg -n "X-Tenant-ID" apps/api-gateway/src/api/middleware/security.py
  ```
- Validate workflow storage includes tenant IDs:
  ```bash
  rg -n "tenant_id" apps/workflow-service/src/workflow_storage.py
  ```

### Implementation status

- **Implemented:** Tenant headers, JWT validation, RBAC enforcement, and tenant-scoped data records.
- **Implemented:** Namespace-per-tenant isolation and automated provisioning scripts in `ops/infra/tenancy/`.

### Related docs

- Security Architecture
- [0005 Rbac Abac Field Level Security](adr/0005-rbac-abac-field-level-security.md)
- Data Classification

---

## Human-in-the-Loop

This platform extends human oversight to critical autonomous decisions, not only formal approval workflows.

### Critical actions under review

The orchestrator evaluates agent-proposed actions against `ops/ops/config/human_review.yaml` rules. Current high-impact checkpoints include:

- **Risk mitigation recommendations** from the Risk Management agent when `risk_score` is above threshold.
- **Schedule adjustments** from the Schedule Planning agent when timeline impact is material.
- **Resource reallocations** from the Resource Management agent when a significant percentage shift is proposed.

### Review configuration

Rules are configured in `ops/ops/config/human_review.yaml` under `review_rules`:

- `action_type`: canonical action category emitted by an agent.
- `agent_ids`: agent identifiers subject to the rule.
- `conditions`: field/operator/value checks against action and result payload content.
- `decision_timeout_seconds`: max wait for a reviewer decision before defaulting to reject.

### Runtime flow

1. Agent task completes and returns proposed actions.
2. Orchestrator checks actions against configured human-review rules.
3. If matched, orchestrator pauses that action and emits `human_review_required` with:
   - correlation ID
   - task and agent IDs
   - proposed action details
   - relevant context/dependency/result data
4. Orchestrator awaits `human_review_decision` (`approve`, `reject`, `modify`).
5. Orchestrator applies decision:
   - `approve`: action proceeds with `approved_by_human_review` status.
   - `reject`: action marked `rejected_by_human_review` and should be skipped by downstream handlers.
   - `modify`: action payload overwritten with reviewer-provided `modified_action` and marked `modified_by_human_review`.

### Review queue for tests

The orchestrator maintains an in-memory queue of pending reviews and exposes it via `get_pending_human_reviews()` to support deterministic tests and local tooling.

### Event contract summary

- **Outbound:** `human_review_required`
- **Inbound:** `human_review_decision`

Both events include `review_id` for correlation; the orchestrator also propagates the workflow-level `correlation_id`.

---

## Feedback Architecture

This repository includes a built-in feedback capture path so clients can collect explicit user quality signals for agent responses and store them for offline analysis and model improvement.

### What was added

- A typed feedback model in `packages/feedback/feedback_models.py`.
- A persistence service in `services/feedback_service.py` backed by SQLite.
- `BaseAgent.send_feedback(...)` for associating feedback to a specific run via `correlation_id`.
- A `request_feedback` boolean added to the standard `AgentResponse` contract.

### Feedback schema

`Feedback` is a dataclass with:

- `correlation_id`: run-level correlation identifier (required).
- `agent_id`: agent identifier the feedback applies to (required).
- `user_rating`: integer score from 1 to 5.
- `comments`: free-form user commentary.
- `corrected_response`: optional user-provided correction.

Validation rules:

- `user_rating` must be in range `1..5`.
- `correlation_id` and `agent_id` must be non-empty.

### Enabling feedback prompts in agent responses

`AgentResponse` now includes `request_feedback`.

- Default: `False`.
- To enable for a specific agent instance, set config:

```python
agent = SomeAgent(
    agent_id="my-agent",
    config={
        "request_feedback": True,
    },
)
```

When true, clients should render a feedback form after showing the response.

### Persisting feedback

`BaseAgent` constructs a `FeedbackService` and exposes:

```python
agent.send_feedback(feedback)
```

Where `feedback` can be either:

- a `Feedback` instance, or
- a `dict` that can be parsed into `Feedback`.

If `feedback.agent_id` does not match the current agent instance, the call raises `ValueError`.

#### Storage backend

- Default SQLite file: `data/feedback.sqlite3`.
- Override via agent config key `feedback_db_path` or env var `FEEDBACK_DB_PATH`.

Schema (`feedback` table):

- `correlation_id`
- `agent_id`
- `user_rating`
- `comments`
- `corrected_response`
- `created_at`

### How feedback is used

Collected feedback can be used to:

- identify low-rated responses by intent/agent,
- analyze recurring failure patterns from comments,
- build supervised datasets from `corrected_response`,
- prioritize prompt/tooling/model improvements per agent.

A typical flow:

1. Agent executes and returns `correlation_id` + `request_feedback`.
2. UI/API gathers rating and optional correction from user.
3. API layer calls `agent.send_feedback(...)`.
4. Offline analytics jobs query feedback records for quality dashboards and training inputs.

---

## Design Review Notes

### Executive Summary

This section provides a comprehensive architectural critique of the Multi-Agent PPM Platform, an AI-native Project Portfolio Management system comprising 25 specialized agents, 40+ external connectors, and a microservices-based backend deployed on Azure with Kubernetes. The review identifies 9 categories of design concerns and 30+ specific opportunities for improving the platform's functionality, reliability, scalability, and maintainability.

---

### 1. Agent Architecture & Orchestration

#### Strengths

- The DAG-based orchestration model in `agents/runtime/src/orchestrator.py` is well-designed, with proper cycle detection, topological ordering, semaphore-bounded parallel execution, and shared context management.
- The `BaseAgent` class (`agents/runtime/src/base_agent.py`) enforces a consistent lifecycle (initialize, validate, process, cleanup) with built-in policy evaluation, audit emission, and tracing, which creates a strong contract across all 25 agents.
- The `AgentRun` state machine (`agents/runtime/src/models.py:92-133`) with explicit transition validation prevents invalid lifecycle states.

#### Concerns & Improvement Opportunities

**1.1 — No Agent Versioning or Canary Deployment Model**

Agents are loaded as singletons at startup without any concept of versioning. If the Business Case agent is updated with a new ROI calculation formula, there is no mechanism to run old and new versions side-by-side, perform A/B testing, or gradually roll out changes. The agent catalog in `agents/runtime/src/agent_catalog.py` maps static IDs to agents with no version field.

*Recommendation:* Add a `version` field to the agent catalog and support routing a percentage of traffic to specific agent versions. This enables canary releases and rollbacks without full redeployments.

**1.2 — Tight Coupling Between Orchestrator and Agent Instances**

The `AgentTask` dataclass (`orchestrator.py:54-58`) holds a direct reference to a `BaseAgent` instance. This means the orchestrator can only invoke agents that are co-located in the same process. The Response Orchestration agent addresses this partially with HTTP invocation, but the core `Orchestrator` class itself cannot natively dispatch to remote agents.

*Recommendation:* Introduce an `AgentProxy` abstraction that the orchestrator uses instead of direct `BaseAgent` references. An `AgentProxy` can resolve to a local instance, an HTTP endpoint, or an event bus topic, making the orchestration engine deployment-topology agnostic.

**1.3 — Missing Backpressure and Priority Queuing**

The orchestrator uses a simple `asyncio.Semaphore` with a fixed `max_parallel_tasks=4` limit. There is no priority differentiation — a low-priority analytics query consumes the same slot as a high-priority approval workflow. When the system is under load, all work is treated equally.

*Recommendation:* Implement a priority queue within the orchestrator that considers urgency metadata from the intent router. High-priority workflows (approval decisions, risk alerts) should preempt or be scheduled ahead of batch analytics.

**1.4 — Agent Process Method Returns Untyped `Any`**

The abstract `process()` method signature (`base_agent.py:95`) returns `Any`, and the `_normalize_payload` method at line 336 attempts to coerce the result into an `AgentPayload`. This is fragile — if an agent returns an unexpected type, the error surfaces at runtime rather than at development time.

*Recommendation:* Define typed return models per agent or at minimum constrain the `process()` return type to `dict[str, Any] | AgentPayload | BaseModel`. Consider a generic `BaseAgent[T]` pattern where `T` is the agent's response model.

**1.5 — Global Orchestrator Singleton**

In `apps/api-gateway/src/api/main.py:126`, the orchestrator is stored as a module-level global variable and also on `app.state`. This creates dual state management and makes testing harder, as the global must be patched independently of the app state.

*Recommendation:* Remove the module-level global. Use only `app.state.orchestrator` and inject it via FastAPI's dependency injection system. This simplifies testing and eliminates the risk of the two references diverging.

---

### 2. Inter-Agent Communication & Event Bus

#### Strengths

- The event bus abstraction via Protocol class (`agents/runtime/src/event_bus.py:17-28`) allows pluggable implementations (Azure Service Bus in production, in-memory for tests).
- Topic-based pub/sub with well-defined event types (`orchestrator.task.started`, `approval.created`, etc.) provides a clean communication vocabulary.

#### Concerns & Improvement Opportunities

**2.1 — Event Bus Singleton Raises on Missing Configuration**

The `get_event_bus()` function (`packages/event-bus/src/event_bus/__init__.py:15-37`) raises a `ValueError` if `AZURE_SERVICE_BUS_CONNECTION_STRING` is unset. This makes it impossible to run the system locally without Azure Service Bus or a mock, since the singleton is eagerly initialized.

*Recommendation:* Introduce an `InMemoryEventBus` implementation that conforms to the `EventBus` protocol and use it as the default fallback when no connection string is configured. This already exists implicitly in the test utilities but should be a first-class production-path default for local development.

**2.2 — No Event Schema Registry or Versioning**

Event payloads are untyped `dict[str, Any]`. There is no schema registry, no schema evolution strategy, and no backward compatibility guarantees. If the Approval Workflow agent changes the shape of `approval.created` events, consumers silently break.

*Recommendation:* Define Pydantic models for all event payloads (e.g., `ApprovalCreatedEvent`, `TaskCompletedEvent`). Publish events through a typed helper that validates the payload against the model before sending. Version the event schemas and include a `schema_version` field in every published event.

**2.3 — Publish Opens and Closes the Service Bus Client on Every Call**

In `packages/event-bus/src/event_bus/service_bus.py:62`, the `publish()` method uses `async with self._client:` which opens and closes the connection on every publish call. This is extremely expensive for high-throughput scenarios and defeats connection pooling.

*Recommendation:* Manage the Service Bus client lifecycle at the application level (startup/shutdown), not per-publish. Keep the sender open and reuse it across publishes. The `start()`/`stop()` methods already exist for the listener loop; apply the same pattern to publishing.

**2.4 — No Dead Letter Queue or Poison Message Handling**

The `_handle_message` method (`service_bus.py:112-131`) either completes or abandons messages. Repeatedly failing messages will be abandoned and retried indefinitely (up to the Service Bus max delivery count), but there is no explicit dead-letter routing or alerting when messages fail persistently.

*Recommendation:* Configure Azure Service Bus dead-letter queues and add a monitoring handler that alerts when messages land in the DLQ. Implement a `_handle_poison_message` method that logs the full payload and emits an observability event.

---

### 3. Data Architecture & State Management

#### Strengths

- Multi-tenancy is enforced at the data model level with `tenant_id` on every table, indexed for query performance.
- The migration strategy using Alembic with numbered, sequential revisions provides a clear evolution path.
- JSON Schema definitions in `data/schemas/` provide an external contract for data validation.

#### Concerns & Improvement Opportunities

**3.1 — SQLAlchemy Models Lack Foreign Key Constraints**

The data models in `data/migrations/models.py` reference parent entities by ID (e.g., `Program.portfolio_id`, `Project.program_id`, `WorkItem.project_id`) but define no `ForeignKey` constraints or SQLAlchemy `relationship()` definitions. This means the database does not enforce referential integrity, orphaned records can accumulate silently, and there are no ORM-level cascade behaviors.

*Recommendation:* Add explicit `ForeignKey` constraints with appropriate `ondelete` behavior (CASCADE or SET NULL). Define SQLAlchemy `relationship()` attributes for navigable object graphs. This catches data integrity issues at the database level rather than relying on application logic.

**3.2 — Connector Configuration Stored in Local JSON Files**

The `ConnectorConfigStore` (`connectors/sdk/src/base_connector.py:383-503`) persists configuration to a local JSON file (`data/connectors/config.json`). In a Kubernetes environment with multiple API replicas, each pod has its own copy of the file, changes on one pod are invisible to others, and there is no transactional guarantee on concurrent read-modify-write operations.

*Recommendation:* Migrate connector configuration storage to the PostgreSQL database or a shared Redis store. If the JSON file approach is retained for local development simplicity, add a database-backed `ConnectorConfigStore` implementation for production deployments.

**3.3 — Memory Store Has No Eviction Policy for In-Memory Implementation**

The `InMemoryConversationStore` (`agents/runtime/src/memory_store.py:26-36`) has no upper bound on stored entries. In a long-running process handling many orchestration runs, this will grow without limit, eventually causing memory exhaustion.

*Recommendation:* Add a max-entries parameter with LRU eviction to the in-memory store. For the Redis store, ensure TTL is always set in production configurations and document the recommended TTL value based on typical orchestration run duration.

**3.4 — No Soft Delete or Audit Trail on Entity Mutations**

The data models support an `AuditEvent` table for logging actions, but the core entity models (Portfolio, Project, etc.) have no soft-delete mechanism. When entities are deleted, they are physically removed from the database, which makes forensic analysis and regulatory compliance harder.

*Recommendation:* Add a `deleted_at` nullable timestamp to all core entities. Implement soft delete at the ORM level and add a query filter that excludes soft-deleted records by default.

**3.5 — Schema Inconsistency Between JSON Schemas and SQLAlchemy Models**

The JSON schemas in `data/schemas/` and the SQLAlchemy models in `data/migrations/models.py` are independently maintained with no automated validation that they stay in sync.

*Recommendation:* Generate one from the other, or add a CI check that validates the JSON schemas against the SQLAlchemy model definitions. Pydantic models that serve both as API schemas and ORM mappers (via `sqlmodel` or similar) would eliminate this dual-maintenance burden entirely.

---

### 4. Security & Authorization

#### Strengths

- Multi-layer security with RBAC + ABAC + classification-based access provides defense in depth.
- The OIDC/JWT validation supports multiple identity providers with JWKS discovery.
- Field-level masking middleware transparently redacts sensitive fields based on user roles.
- Wildcard CORS origins are blocked in non-development environments (`main.py:102-103`).

#### Concerns & Improvement Opportunities

**4.1 — RBAC Configuration Loaded from Disk on Every Request**

The `_load_rbac()` function (`middleware/security.py:39-43`) reads YAML files from disk on every invocation. Both `AuthTenantMiddleware` and `FieldMaskingMiddleware` call this function per request. In high-throughput scenarios, this is a significant performance bottleneck.

*Recommendation:* Cache the parsed RBAC configuration in memory with a configurable refresh interval (e.g., reload every 60 seconds or on SIGHUP). Consider using a file watcher for development mode that hot-reloads on change.

**4.2 — OIDC Configuration Cache Never Expires**

The `_OIDC_CONFIG_CACHE` dictionary (`security.py:141`) stores OIDC discovery documents indefinitely. If the identity provider rotates its signing keys, the cached JWKS data becomes stale, and token validation may fail or accept revoked tokens.

*Recommendation:* Add TTL-based expiration to the OIDC cache (e.g., 1 hour) or use the HTTP `Cache-Control` headers from the discovery response to determine cache lifetime.

**4.3 — FieldMaskingMiddleware Reads the Entire Response Body into Memory**

The `FieldMaskingMiddleware` (`security.py:488-516`) reads the entire response body via `b"".join([chunk async for chunk in response.body_iterator])`, parses it as JSON, masks fields, and re-serializes. For large responses (e.g., bulk data exports), this doubles memory consumption and blocks the event loop during serialization.

*Recommendation:* For responses exceeding a configurable threshold (e.g., 1 MB), apply masking at the query level rather than as a response post-processor. Alternatively, stream the JSON transformation using an incremental parser.

**4.4 — Dev Mode Authentication Bypass Lacks Guardrails**

The `ops/config/.env.example` references `AUTH_MODE=dev` and `X-Dev-User` headers. If a production deployment accidentally sets `AUTH_MODE=dev`, the entire authentication layer could be bypassed.

*Recommendation:* Add a startup check that prevents `AUTH_MODE=dev` when `ENVIRONMENT` is `production` or `staging`. Log a clear warning when dev mode is active.

---

### 5. Connector & Integration Layer

#### Strengths

- The connector SDK (`connectors/sdk/src/base_connector.py`) provides a clean abstraction with consistent interface methods (authenticate, test_connection, read, write).
- Mutual exclusivity enforcement per category prevents conflicting integrations.
- MCP (Model Context Protocol) integration allows agents to interact with connectors through a standardized tool interface.

#### Concerns & Improvement Opportunities

**5.1 — Connector Interface is Synchronous**

The `BaseConnector` methods (`authenticate`, `test_connection`, `read`, `write`) are all synchronous. This blocks the event loop when called from async agent code, reducing throughput under concurrent load.

*Recommendation:* Define async versions of all connector methods (`async def authenticate`, `async def read`, etc.). For connectors that wrap synchronous HTTP libraries, use `asyncio.to_thread()` as a bridge.

**5.2 — ConnectorConfig Mixes Secrets and Non-Secrets in the Same Dataclass**

The `ConnectorConfig` dataclass (`base_connector.py:109-252`) stores `mcp_client_secret`, `mcp_api_key`, `mcp_oauth_token`, and `client_secret` alongside non-sensitive fields like `instance_url` and `sync_frequency`. When serialized via `to_dict()`, secrets are included in the output and may be exposed through logs, caches, or API responses.

*Recommendation:* Separate `ConnectorConfig` into a `ConnectorConfig` (non-sensitive settings) and a `ConnectorCredentials` object (secrets). Override `__repr__` and serialization methods on the credentials object to never include raw secret values. Secrets should only be resolved at the point of use from Azure Key Vault, never persisted in JSON.

**5.3 — No Connection Health Monitoring**

Connectors have a `test_connection()` method, but it is only invoked on-demand. There is no periodic health check that proactively detects when an external system becomes unreachable, or when OAuth tokens expire.

*Recommendation:* Implement a background health-check scheduler that periodically calls `test_connection()` on all enabled connectors and updates their `health_status` field. Surface unhealthy connectors through the monitoring dashboard and the System Health agent.

**5.4 — No Rate Limiting for Outbound Connector Calls**

Connectors make outbound HTTP calls to external systems (Jira, Azure DevOps, SAP, etc.) without any client-side rate limiting. A bulk sync of thousands of work items could overwhelm an external system's API limits, resulting in throttling or account suspension.

*Recommendation:* Add a configurable rate limiter per connector (e.g., using a token bucket algorithm) that respects the external system's published API limits. Include backoff logic that responds to HTTP 429 (Too Many Requests) responses.

---

### 6. Observability & Resilience

#### Strengths

- Comprehensive observability stack with OpenTelemetry tracing, Prometheus metrics, structured logging, and Azure Monitor integration.
- Correlation ID propagation across the entire request lifecycle enables end-to-end tracing.
- Circuit breaker pattern in the Response Orchestration agent prevents cascading failures.
- SLO definitions and alert rules demonstrate a mature operational posture.

#### Concerns & Improvement Opportunities

**6.1 — Circuit Breaker State is In-Memory Per Instance**

The circuit breaker in the Response Orchestration agent tracks `failure_counts` in instance memory. In a multi-replica deployment, each pod maintains its own circuit breaker state. One pod may have an open circuit while others continue sending requests to the failing agent.

*Recommendation:* Share circuit breaker state in Redis so all replicas have a consistent view of agent health. Alternatively, use the health check infrastructure to centrally track agent availability.

**6.2 — No Graceful Degradation Strategy**

When an agent fails, the orchestrator records the failure and moves on. There is no defined degradation strategy — for example, if the Analytics Insights agent is unavailable, the system could still return partial results from other agents rather than failing the entire orchestration.

*Recommendation:* Define per-agent criticality levels (critical, important, optional). The orchestrator should require critical agents to succeed, warn on important agent failures, and silently skip optional agents. This allows the system to provide partial results rather than total failure.

**6.3 — Retry Policy Uses Random Jitter Without Decorrelation**

The backoff implementation (`orchestrator.py:324-328`) adds uniform random jitter up to `jitter_seconds` (0.2s). Under high contention, all retries for the same agent will cluster around similar delay values. Decorrelated jitter provides better spread.

*Recommendation:* Implement the AWS-recommended "full jitter" algorithm: `sleep = random_between(0, min(cap, base * 2^attempt))`. This provides better retry distribution under contention.

**6.4 — No Bulkhead Isolation Between Agent Domains**

All 25 agents share the same semaphore pool (`max_parallel_tasks=4`). A runaway agent that is slow or resource-heavy can starve all other agents of execution slots. There is no isolation between domain areas (portfolio management vs. delivery management vs. operations).

*Recommendation:* Implement bulkhead isolation by allocating separate semaphore pools per agent domain. For example, core orchestration agents get 2 dedicated slots, portfolio agents get 4, and delivery agents get 4. This prevents one domain from monopolizing all execution capacity.

---

### 7. Code Organization & Developer Experience

#### Strengths

- Comprehensive documentation in `docs/architecture/` with 17+ architecture documents.
- Consistent project structure across all services (`src/`, `tests/`, `helm/`, `contracts/`).
- Strong code quality enforcement with Black, Ruff, MyPy (strict mode), and Bandit.
- Makefile targets provide a unified development workflow.

#### Concerns & Improvement Opportunities

**7.1 — Brittle `sys.path` Manipulation for Cross-Package Imports**

Multiple files use `sys.path.insert()` to resolve cross-package imports:

- `base_agent.py:16-18`: Adds `packages/observability/src`
- `orchestrator.py:24-28`: Adds `packages/feature-flags/src`
- `main.py:44-50`: Adds 4 separate package roots
- `event_bus.py:9-12`: Adds `packages/event_bus/src`

This pattern is fragile, order-dependent, and makes it difficult to reason about module resolution. It creates hidden dependencies and breaks IDE navigation and type checking.

*Recommendation:* Use proper Python packaging with `pyproject.toml` for each package and install them in development mode (`pip install -e packages/observability`). This eliminates all `sys.path` manipulation and makes dependencies explicit.

**7.2 — Deprecated FastAPI Event Hooks**

The startup and shutdown handlers in `main.py:129-181` use `@app.on_event("startup")` and `@app.on_event("shutdown")`, which are deprecated in FastAPI. The recommended approach is to use `lifespan` context managers.

*Recommendation:* Migrate to FastAPI's `lifespan` parameter using an async context manager. This provides cleaner resource management and is the supported path going forward.

**7.3 — Inconsistent Use of Pydantic vs Dataclasses**

The codebase mixes Pydantic `BaseModel` (for `AgentResponse`, `AgentRun`, `AgentPayload`), Python `dataclass` (for `AgentTask`, `RetryPolicy`, `OrchestrationResult`, `ConnectorConfig`), and plain dictionaries (for most inter-agent payloads). This inconsistency means some data structures get automatic validation and serialization while others do not.

*Recommendation:* Standardize on Pydantic models for all domain objects that cross service boundaries (API requests/responses, event payloads, agent I/O). Use dataclasses or `NamedTuple` for internal-only value objects that do not need validation.

**7.4 — Large Number of Environment Variables Without Centralized Validation**

The `ops/config/.env.example` file contains 150+ environment variables. These are read via scattered `os.getenv()` calls throughout the codebase with inconsistent default values and no centralized validation at startup. A typo in an environment variable name silently falls through to a default value.

*Recommendation:* Define a Pydantic `Settings` class (building on the existing `pydantic_settings.py`) that declares all environment variables with types, defaults, and validation rules. Load and validate this at application startup. Any missing or invalid configuration should fail fast with a clear error message rather than silently degrading.

---

### 8. Frontend Architecture

#### Strengths

- Clean separation with Zustand stores provides lightweight, composable state management.
- Internationalization support (i18n) with React Intl and multiple locales.
- Accessibility testing with axe-core demonstrates a commitment to inclusive design.
- Error boundary wrapping the entire application provides crash recovery.

#### Concerns & Improvement Opportunities

**8.1 — No API Client Abstraction Layer**

The frontend stores make direct `fetch()` calls without a centralized API client. Authentication headers, error handling, retry logic, and base URL configuration are duplicated across stores. If the API changes its authentication scheme or error format, every store must be updated.

*Recommendation:* Implement a centralized API client (e.g., using `axios` with interceptors, or a typed `fetch` wrapper) that handles authentication token injection, automatic retry on 401/503, error normalization, and base URL management. All stores should use this client rather than raw `fetch`.

**8.2 — Frontend Logging is Console-Only**

Error logging uses `console.error()` calls with ad-hoc context objects. In production, these logs are lost unless the browser's console output is captured by an external tool.

*Recommendation:* Integrate a structured logging library that can ship errors to a backend telemetry endpoint (e.g., the existing telemetry service). At minimum, unhandled errors from the ErrorBoundary should be reported to the backend for correlation with server-side traces.

**8.3 — 28 Routes Without Code Splitting**

The `App.tsx` component defines 28 routes. Without code splitting, the initial bundle includes all page components, increasing the initial load time.

*Recommendation:* Use React's `lazy()` and `Suspense` for route-level code splitting. Each page should be loaded on demand, reducing the initial bundle size significantly for enterprise users who typically access a subset of features.

**8.4 — No Optimistic Updates or Offline Support**

The frontend follows a purely request-response pattern with no optimistic updates. For operations like saving a project configuration or approving a workflow, the user must wait for the server response before the UI updates.

*Recommendation:* For common write operations, implement optimistic updates in the Zustand stores (update state immediately, reconcile on server response). Consider adding service worker caching for read-heavy views like dashboards to improve perceived performance.

---

### 9. Testing & Quality Assurance

#### Strengths

- Comprehensive test taxonomy: unit, integration, e2e, contract, load, security, performance, accessibility.
- 80% coverage minimum enforced in CI.
- Docker Compose test environment with PostgreSQL and Redis for realistic integration testing.
- Performance smoke tests run on PRs with regression detection.

#### Concerns & Improvement Opportunities

**9.1 — No Chaos Engineering or Fault Injection**

The test suite validates correct behavior but does not systematically test failure modes. There are no tests for scenarios such as: what happens when Redis is unavailable mid-orchestration, when an agent times out after partial completion, or when the database is read-only.

*Recommendation:* Add fault injection tests using tools like `toxiproxy` or programmatic network fault simulation. Test the platform's behavior when each infrastructure dependency is degraded (high latency, packet loss, connection refused).

**9.2 — Only 13 Frontend Test Files**

The frontend has 28 routes, 7 Zustand stores, and dozens of components, but only 13 test files. This suggests limited coverage of user interactions and state management edge cases.

*Recommendation:* Increase frontend test coverage with a focus on store behavior under error conditions, component interactions for critical workflows (approval decisions, connector configuration), and integration tests for the API client layer.

**9.3 — No Multi-Agent Integration Tests**

Individual agents have unit tests, and there are e2e tests for user journeys, but there appear to be no integration tests that exercise the actual multi-agent orchestration pipeline: Intent Router → Response Orchestrator → Domain Agents → Aggregation.

*Recommendation:* Add integration tests that exercise the full orchestration flow with mocked LLM responses but real agent logic. Test scenarios like: a user query that requires 3 agents where one fails; a query that triggers the approval workflow; and a query with circular agent dependencies.

**9.4 — Load Tests Missing Multi-Tenant Simulation**

The load testing infrastructure exists but does not simulate multi-tenant scenarios where multiple tenants issue concurrent requests with different configurations, data volumes, and access patterns.

*Recommendation:* Extend load tests to simulate realistic multi-tenant workloads. Test that tenant isolation holds under concurrent load and that one tenant's heavy usage does not degrade another tenant's performance.

---

### Summary of Priority Recommendations

#### Critical (address before production)

| # | Area | Recommendation |
|---|------|----------------|
| 1 | Event Bus | Fix per-publish connection lifecycle — open/close on every publish is a performance killer (`service_bus.py:62`) |
| 2 | Security | Cache RBAC configuration instead of reading YAML from disk on every request (`security.py:39-43`) |
| 3 | Data | Add foreign key constraints to SQLAlchemy models — no referential integrity is a data corruption risk |
| 4 | Connector | Separate secrets from ConnectorConfig — credentials are included in `to_dict()` output |
| 5 | State | Migrate connector config from local JSON files to database for multi-replica consistency |

#### High (significant capability improvements)

| # | Area | Recommendation |
|---|------|----------------|
| 6 | Agent | Introduce agent versioning and canary deployment support |
| 7 | Event Bus | Define typed event schemas with versioning |
| 8 | Resilience | Add bulkhead isolation between agent domains |
| 9 | Resilience | Share circuit breaker state across replicas |
| 10 | Code | Eliminate `sys.path` manipulation with proper Python packaging |
| 11 | Connector | Make connector interface async |
| 12 | Frontend | Add centralized API client with retry and auth handling |

#### Medium (quality and maintainability)

| # | Area | Recommendation |
|---|------|----------------|
| 13 | Agent | Add priority queuing to orchestrator |
| 14 | Agent | Define typed `process()` return types per agent |
| 15 | Security | Add TTL to OIDC configuration cache |
| 16 | Connector | Add background health monitoring for connectors |
| 17 | Connector | Add client-side rate limiting for outbound calls |
| 18 | Frontend | Implement route-level code splitting |
| 19 | Frontend | Integrate frontend error reporting with backend telemetry |
| 20 | Testing | Add multi-agent orchestration integration tests |
| 21 | Testing | Add fault injection / chaos engineering tests |
| 22 | Code | Migrate to FastAPI lifespan handlers |
| 23 | Code | Centralize environment variable validation with Pydantic Settings |
| 24 | Data | Add soft delete to core entities |

---

### Conclusion

The Multi-Agent PPM Platform demonstrates substantial architectural ambition and many well-considered design decisions. The DAG-based orchestration engine, multi-layer security model, comprehensive observability stack, and structured agent lifecycle are strong foundations.

The most impactful improvements fall into three themes:

1. **Production hardening**: Fix the per-publish connection lifecycle in the event bus, cache security configuration, enforce database referential integrity, and separate credential management from configuration.

2. **Multi-replica consistency**: Move all stateful components (connector config, circuit breaker state, agent configuration) out of local process memory and into shared stores (PostgreSQL, Redis) to support horizontal scaling in Kubernetes.

3. **Agent evolution**: Add versioning, typed contracts, and priority-aware scheduling to the agent framework so that the platform can evolve its 25 agents independently without requiring coordinated deployments.

Addressing the critical and high-priority items would significantly improve the platform's reliability and operability in production multi-tenant environments.

---

## Architecture Decision Records

The following ADRs document key architectural decisions made during platform design.

| ADR | Title |
| --- | --- |
| [ADR 0000 — ADR Template](adr/0000-adr-template.md) | Template for recording architecture decisions |
| [ADR 0001 — Record Architecture Decisions](adr/0001-record-architecture.md) | Adopt ADRs as the mechanism for recording significant decisions |
| [ADR 0002 — LLM Provider Abstraction](adr/0002-llm-provider-abstraction.md) | Abstract LLM providers behind a unified interface |
| [ADR 0003 — Eventing and Message Bus](adr/0003-eventing-and-message-bus.md) | Use Azure Service Bus for async event delivery |
| [ADR 0004 — Workflow Service Selection](adr/0004-workflow-service-selection.md) | Select Temporal as the durable workflow engine |
| [ADR 0005 — RBAC, ABAC, and Field-Level Security](adr/0005-rbac-abac-field-level-security.md) | Layered access control model |
| [ADR 0006 — Data Lineage and Audit](adr/0006-data-lineage-and-audit.md) | Immutable lineage events and WORM audit log |
| [ADR 0007 — Connector Certification](adr/0007-connector-certification.md) | Maturity gate process for connector promotion |
| [ADR 0008 — Prompt Management and Versioning](adr/0008-prompt-management-and-versioning.md) | Version-controlled prompt templates |
| [ADR 0009 — Multi-Tenancy Strategy](adr/0009-multi-tenancy-strategy.md) | Shared-infrastructure logical isolation model |
| [ADR 0010 — Secrets Management](adr/0010-secrets-management.md) | Azure Key Vault with SecretProviderClass injection |
