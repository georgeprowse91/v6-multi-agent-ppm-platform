# Agents Documentation

## Purpose

Central navigation hub for all agent-related documentation. Links to the canonical specs, architecture docs, configuration reference, and code-adjacent index.

## Where to find agent files

| What you need | Where to find it |
| --- | --- |
| Detailed agent specs (inputs, outputs, behaviour) | [`docs/product/02-solution-design/agent-system-design.md`](/docs/product/02-solution-design/agent-system-design.md) |
| Architecture — how agents orchestrate | [`docs/architecture/agent-orchestration.md`](/docs/architecture/agent-orchestration.md) |
| Architecture — runtime lifecycle and state | [`docs/architecture/agent-runtime.md`](/docs/architecture/agent-runtime.md) |
| Code-adjacent catalog with links to each agent's README | [`agents/AGENT_CATALOG.md`](/agents/AGENT_CATALOG.md) |
| All agent configuration files | [`ops/config/agents/`](/ops/config/agents/) |
| Agent source code | `agents/{category}/agent-{NN}-{name}/src/` |

## Agent quick-reference (25 agents)

| Agent | Purpose | Inputs | Outputs | Interfaces | Dependencies | Example invocation |
| --- | --- | --- | --- | --- | --- | --- |
| **Agent 01 – Intent Router** | Classify user intent and route to domain agents. | User query, context. | Top-2 intent predictions, confidence-scored multi-intent routing plan, validated entities. | API gateway, agent runner. | Agent registry, policy guardrails, transformer classifier, spaCy entity extraction. | `{"text":"Show project risks and budget"}` → `intents:[risk_query,financial_query]` |
| **Agent 02 – Response Orchestration** | Build multi-step plan and compose response. | Intent, plan constraints. | Agent call sequence, final response. | Orchestration runtime. | Policy guardrails, state store. | `{"intent":"create_project"}` → `plan:[A8,A10]` |
| **Agent 03 – Approval Workflow** | Coordinate approvals and stage gates. | Gate criteria, approvers. | Approval decision, audit log. | Workflow engine, notifications. | RBAC/ABAC, audit events. | `{"gate":"Initiation","project":"PROJ-1"}` |
| **Agent 04 – Demand & Intake** | Capture demand from channels. | Intake form, email, CRM. | Demand record. | API, connector events. | CRM connectors, schema validator. | `{"source":"salesforce","type":"request"}` |
| **Agent 05 – Business Case & Investment** | Build ROI and cost-benefit. | Demand record, cost inputs. | Business case, ROI metrics. | API, analytics store. | Financial data, templates. | `{"project":"PROJ-1","roi":true}` |
| **Agent 06 – Portfolio Strategy & Optimization** | Prioritize portfolio with constraints. | Candidate projects, capacity. | Ranked portfolio, scenario. | API, analytics. | Resource agent, finance agent. | `{"portfolio":"FY26","budget":5000000}` |
| **Agent 07 – Program Management** | Manage program structure, dependencies, health, and integrations. | Project list, dependencies, schedule/cost/risk signals. | Program roadmap, dependency map, health narrative. | API, events. | Cosmos DB, Azure ML, Azure OpenAI, Planview/Clarity, Jira/Azure DevOps, Service Bus, Synapse, Text Analytics, schedule agent. | `{"program":"Payments","projects":["P1","P2"]}` |
| **Agent 08 – Project Definition & Scope** | Draft charter and scope baseline. | Demand, business case. | Charter, scope items. | API, document store. | Knowledge agent, templates. | `{"demand":"D-1001","template":"charter"}` |
| **Agent 09 – Project Lifecycle & Governance** | Enforce phase transitions. | Stage gates, status. | Gate decisions, lifecycle updates. | Workflow engine. | Approval agent, compliance agent. | `{"project":"PROJ-1","stage":"Planning"}` |
| **Agent 10 – Schedule & Planning** | Build schedules/WBS from scope. | Scope items, constraints. | WBS, schedule baseline. | API, calendar integration. | Resource agent, vendor agent. | `{"project":"PROJ-1","horizon":"Q3"}` |
| **Agent 11 – Resource & Capacity** | Manage allocation and capacity. | Resource pool, demand. | Allocation plan. | API, HR connector. | HR data, schedule agent. | `{"skill":"QA","fte":2}` |
| **Agent 12 – Financial Management** | Track budgets, actuals, forecasts, and profitability. | Budget baseline, actuals, approvals context, currency data. | Variance/EVM reports, forecasts, profitability metrics. | API, ERP connector, Service Bus. | ERP finance connectors, approval workflow, Key Vault secrets, related agent endpoints. | `{"project":"PROJ-1","action":"analyze_variance"}` |
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

## Agent configuration reference

All agent runtime configuration lives under `ops/config/agents/`. The table below covers the key files:

| File | Purpose | Key fields |
| --- | --- | --- |
| `ops/config/agents/intent-routing.yaml` | Intent definitions and routing targets (canonical design reference). | `intents[].name`, `intents[].routes[].agent_id`, `intents[].routes[].action` |
| `ops/config/agents/orchestration.yaml` | Intent routing + response orchestration settings. | `intent_router.model.*`, `intent_router.intents`, `response_orchestration.max_concurrency`, `response_orchestration.retry_policy.*` |
| `ops/config/agents/portfolio.yaml` | Domain agent configuration for demand, business case, portfolio strategy, and program management. | `demand_intake.*`, `business_case.*`, `portfolio_strategy.*`, `program_management.*` |
| `ops/config/agents/demo-participants.yaml` | Demo participant configuration for local and demo environments. | `participants[].name`, `participants[].role` |
| `ops/config/agents/data-synchronisation-agent/` | Per-agent config for Agent 23 (data sync): mapping rules, quality thresholds, pipelines, schema registry, validation rules. | — |
| `ops/config/agents/workflow-engine-agent/` | Per-agent config for Agent 24 (workflow engine): durable workflow definitions and templates. | — |

> **Note on runtime config:** `services/agent-runtime/src/config/intent-routing.yaml` is a separate runtime-only copy that uses numeric agent IDs (e.g. `agent_015`) matching the IDs registered in `services/agent-runtime/src/runtime.py`. See the comment at the top of that file for details.

## How to run / develop / test

Validate internal links across docs:

```bash
python ops/scripts/check-links.py
```

Verify the catalog contains all 25 agents:

```bash
rg -n "Agent 25" agents/AGENT_CATALOG.md
```

## Troubleshooting

- Broken links: run the link checker and fix any relative path mismatches.
- Missing diagrams: verify files exist under `docs/architecture/diagrams/` where referenced.
