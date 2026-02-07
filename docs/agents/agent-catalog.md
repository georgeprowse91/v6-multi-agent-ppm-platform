# Agent Catalog (25 Agents)

## Purpose

Define the full 25-agent ecosystem for the Multi-Agent PPM Platform, including each agent’s role, inputs/outputs, interfaces, dependencies, and a concrete invocation pattern.

## Architecture-level context

Agents form the decision plane of the platform. The Intent Router (Agent 01) classifies requests, the Response Orchestrator (Agent 02) plans multi-step execution, and domain agents (Agents 03–25) own specific PPM capabilities. Agents exchange data using the canonical schemas in `data/schemas/` and integrate through connectors registered in `integrations/connectors/registry/`.

## Catalog

| Agent | Purpose | Inputs | Outputs | Interfaces | Dependencies | Example invocation |
| --- | --- | --- | --- | --- | --- | --- |
| **Agent 01 – Intent Router** | Classify user intent and route to domain agents. | User query, context. | Intent label, routing plan. | API gateway, agent runner. | Agent registry, policy guardrails. | `{"text":"Create a new project"}` → `intent:create_project` |
| **Agent 02 – Response Orchestration** | Build multi-step plan and compose response. | Intent, plan constraints. | Agent call sequence, final response. | Orchestration runtime. | Policy guardrails, state store. | `{"intent":"create_project"}` → `plan:[A8,A10]` |
| **Agent 03 – Approval Workflow** | Coordinate approvals and stage gates. | Gate criteria, approvers. | Approval decision, audit log. | Workflow engine, notifications. | RBAC/ABAC, audit events. | `{"gate":"Initiation","project":"PROJ-1"}` |
| **Agent 04 – Demand & Intake** | Capture demand from channels. | Intake form, email, CRM. | Demand record. | API, connector events. | CRM connectors, schema validator. | `{"source":"salesforce","type":"request"}` |
| **Agent 05 – Business Case & Investment** | Build ROI and cost-benefit. | Demand record, cost inputs. | Business case, ROI metrics. | API, analytics store. | Financial data, templates. | `{"project":"PROJ-1","roi":true}` |
| **Agent 06 – Portfolio Strategy & Optimization** | Prioritize portfolio with constraints. | Candidate projects, capacity. | Ranked portfolio, scenario. | API, analytics. | Resource agent, finance agent. | `{"portfolio":"FY26","budget":5000000}` |
| **Agent 07 – Program Management (Implemented)** | Manage program structure, dependencies, health, and integrations. | Project list, dependencies, schedule/cost/risk signals. | Program roadmap, dependency map, health narrative. | API, events. | Cosmos DB, Azure ML, Azure OpenAI, Planview/Clarity, Jira/Azure DevOps, Service Bus, Synapse, Text Analytics, schedule agent. | `{"program":"Payments","projects":["P1","P2"]}` |
| **Agent 08 – Project Definition & Scope** | Draft charter and scope baseline. | Demand, business case. | Charter, scope items. | API, document store. | Knowledge agent, templates. | `{"demand":"D-1001","template":"charter"}` |
| **Agent 09 – Project Lifecycle & Governance** | Enforce phase transitions. | Stage gates, status. | Gate decisions, lifecycle updates. | Workflow engine. | Approval agent, compliance agent. | `{"project":"PROJ-1","stage":"Planning"}` |
| **Agent 10 – Schedule & Planning** | Build schedules/WBS from scope. | Scope items, constraints. | WBS, schedule baseline. | API, calendar integration. | Resource agent, vendor agent. | `{"project":"PROJ-1","horizon":"Q3"}` |
| **Agent 11 – Resource & Capacity** | Manage allocation and capacity. | Resource pool, demand. | Allocation plan. | API, HR connector. | HR data, schedule agent. | `{"skill":"QA","fte":2}` |
| **Agent 12 – Financial Management** | Track budgets and actuals. | Budget baseline, actuals. | Variance reports. | API, ERP connector. | SAP/Workday connectors. | `{"project":"PROJ-1","currency":"USD"}` |
| **Agent 13 – Vendor & Procurement** | Manage vendor onboarding. | Procurement request. | Vendor record, contract. | API, document store. | Finance agent, compliance agent. | `{"vendor":"Acme","category":"software"}` |
| **Agent 14 – Quality Assurance** | Define QA plans and gates. | Test plans, standards. | QA checklist, status. | API, workflow engine. | Release agent, compliance agent. | `{"project":"PROJ-1","standard":"ISO"}` |
| **Agent 15 – Risk & Issue Management** | Maintain risk/issue logs. | Risk signals, incidents. | Risk register, mitigations. | API, notifications. | Program agent, compliance agent. | `{"risk":"schedule_slip","severity":"high"}` |
| **Agent 16 – Compliance & Security** | Verify compliance posture. | Controls, policy rules. | Compliance assessment. | Policy engine. | Security architecture, audit logs. | `{"control":"SOC2-CC6","project":"PROJ-1"}` |
| **Agent 17 – Change & Configuration** | Track change requests. | Change request, baseline. | Change log, approvals. | Workflow engine. | Approval agent, schedule agent. | `{"change":"scope","impact":"high"}` |
| **Agent 18 – Release & Deployment** | Coordinate releases and cutovers. | Release plan, artifacts. | Release status. | CI/CD systems. | QA agent, operations. | `{"release":"R-2026.1"}` |
| **Agent 19 – Knowledge & Document** | Manage document lifecycle. | Docs, metadata. | Indexed knowledge assets. | Document store. | SharePoint connector. | `{"doc":"Charter","project":"PROJ-1"}` |
| **Agent 20 – Continuous Improvement** | Capture retros and process mining. | Retros, telemetry. | Improvement backlog. | Analytics pipeline. | Observability data. | `{"retro":"Sprint 5","team":"Payments"}` |
| **Agent 21 – Stakeholder & Comms** | Stakeholder updates and comms. | Status signals, milestones. | Notifications, comms plan. | Slack/Teams connectors. | Program agent, schedule agent. | `{"message":"Gate approved","channel":"PMO"}` |
| **Agent 22 – Analytics & Insights** | Dashboards and forecasts. | Canonical data, events. | KPI dashboards. | Analytics store. | Data quality scores. | `{"metric":"portfolio_health"}` |
| **Agent 23 – Data Synchronization & Quality** | Sync and score data quality. | External system data. | Quality scores, sync logs. | Connector runtime. | Mapping engine. | `{"connector":"jira","entity":"work_item"}` |
| **Agent 24 – Workflow & Process Engine** | Execute workflows and gates. | Workflow definitions. | Task execution status. | Workflow engine. | Approval agent. | `{"workflow":"stage_gate","project":"PROJ-1"}` |
| **Agent 25 – System Health & Monitoring** | Monitor platform health. | Metrics/logs/traces. | Alerts, SLO status. | Observability stack. | Monitoring tools. | `{"slo":"api-latency"}` |

## Usage example

Locate the Business Case agent entry:

```bash
rg -n "Business Case" docs/agents/agent-catalog.md
```

## How to verify

Ensure the catalog contains 25 agents:

```bash
rg -n "Agent 25" docs/agents/agent-catalog.md
```

Expected output: a line referencing Agent 25.

## Implementation status

- **Implemented**: agent runtime framework, orchestration APIs, and domain agent registrations via `services/agent-runtime/` and `apps/orchestration-service/`.
- **Implemented**: configuration-driven intent routing and domain agent settings via `config/agents/`.

## Related docs

- [Agent Orchestration](../architecture/agent-orchestration.md)
- [Data Schemas](../../data/schemas/)
- [Connector Overview](../connectors/overview.md)
