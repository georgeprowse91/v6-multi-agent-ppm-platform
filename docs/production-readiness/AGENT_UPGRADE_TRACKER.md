# Agent Upgrade Tracker

Tracking required updates for each of the 25 agents based on the cross-agent foundations rollout.

| Agent | Required updates status | Evidence |
| --- | --- | --- |
| Agent 01 – Intent Router | Done | Loads prompt registry intent routing prompt and uses shared LLM client wrapper, emitting `intent.classified` audit events. |
| Agent 02 – Response Orchestration | Done | Builds dependency-aware DAG execution with retries/circuit breaker, injects trace headers, and emits orchestration audit events. |
| Agent 03 – Approval Workflow | Done | Uses role lookup + delegation records with tenant-scoped durable store, emitting approval audit events. |
| Agent 04 – Demand & Intake | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 05 – Business Case & Investment | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 06 – Portfolio Strategy & Optimization | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 07 – Program Management | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 08 – Project Definition & Scope | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 09 – Project Lifecycle & Governance | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 10 – Schedule & Planning | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 11 – Resource & Capacity | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
| Agent 12 – Financial Management | Done | Inherits shared runtime upgrades (IDs, policy checks, audit logging). |
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
