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
| Agent 13 – Vendor & Procurement | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 14 – Quality Assurance | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 15 – Risk & Issue Management | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 16 – Compliance & Security | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 17 – Change & Configuration | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 18 – Release & Deployment | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 19 – Knowledge & Document | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 20 – Continuous Improvement | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 21 – Stakeholder & Comms | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 22 – Analytics & Insights | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 23 – Data Synchronization & Quality | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 24 – Workflow & Process Engine | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 25 – System Health & Monitoring | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
