# Agent Upgrade Tracker

Tracking required updates for each of the 25 agents based on the cross-agent foundations rollout.

| Agent | Required updates status | Evidence |
| --- | --- | --- |
| Agent 01 – Intent Router | Done | Loads prompt registry intent routing prompt and uses shared LLM client wrapper, emitting `intent.classified` audit events. |
| Agent 02 – Response Orchestration | Done | Builds dependency-aware DAG execution with retries/circuit breaker, injects trace headers, and emits orchestration audit events. |
| Agent 03 – Approval Workflow | Done | Uses role lookup + delegation records with tenant-scoped durable store, emitting approval audit events. |
| Agent 04 – Demand & Intake | Done | Tenant-scoped durable demand store, schema + rule-set validation, and demand.created event publishing. |
| Agent 05 – Business Case & Investment | Done | Tenant-scoped business case store, ROI validation, business_case.created + investment.recommendation events, and new tests. |
| Agent 06 – Portfolio Strategy & Optimization | Done | Portfolio prioritizations persisted, portfolio.prioritized events emitted, and policy guardrails with audit emission on approvals. |
| Agent 07 – Program Management | Done | Program/roadmap/dependency persistence with program.created + program.roadmap.updated events and new tests. |
| Agent 08 – Project Definition & Scope | Done | Charter/WBS persistence, approval workflow sign-off, and charter.created + wbs.created events with new tests. |
| Agent 09 – Project Lifecycle & Governance | Done | Lifecycle state persistence, project.transitioned events, and approval workflow enforcement on gate overrides with updated tests. |
| Agent 10 – Schedule & Planning | Done | Schedule/baseline persistence, schedule.baseline.locked + schedule.delay events, and change-control integration with tests. |
| Agent 11 – Resource & Capacity | Done | Resource/allocations persistence, resource allocation event publishing, schema validation, and new tests. |
| Agent 12 – Financial Management | Done | Tenant-scoped budget/actual/forecast persistence, budget audit events + approvals, schema validation, and expanded tests. |
| Agent 13 – Vendor & Procurement | Done | Vendor/contract/invoice persistence with schema validation and approval workflow integration, plus new tests. |
| Agent 14 – Quality Assurance | Done | Quality artifacts persisted with quality event emission and new tests. |
| Agent 15 – Risk & Issue Management | Done | Risk register persistence with schema/data-quality validation and new tests. |
| Agent 16 – Compliance & Security | Done | Control mapping policy checks, evidence persistence, and new tests. |
| Agent 17 – Change & Configuration | Done | Change/CMDB persistence with approval workflow integration and new tests. |
| Agent 18 – Release & Deployment | Done | Release calendar persistence with approval gating prior to deployment and new tests. |
| Agent 19 – Knowledge & Document | Done | Documents persisted with schema validation; RBAC/ABAC access checks enforced on retrieval. |
| Agent 20 – Continuous Improvement | Done | Event logs persisted and improvement recommendations emitted to workflow engine integration. |
| Agent 21 – Stakeholder & Comms | Done | Stakeholder register persisted with consent/opt-out enforcement on message sends. |
| Agent 22 – Analytics & Insights | Done | Analytics outputs persisted; lineage stored with PII masking. |
| Agent 23 – Data Synchronization & Quality | Done | Master records, sync logs, and lineage persisted; audit events emitted for create/update. |
| Agent 24 – Workflow & Process Engine | Done | Workflow definitions/instances persisted with event triggers and workflow event emission. |
| Agent 25 – System Health & Monitoring | Done | OpenTelemetry metrics/tracing integrated; alerts/incidents persisted with PII redaction. |
