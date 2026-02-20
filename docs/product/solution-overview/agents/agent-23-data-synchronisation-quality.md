> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 23 — Data Synchronisation and Quality

**Category:** Operations Management
**Role:** Data Integrity Guardian and Sync Coordinator

---

## What This Agent Is

The Data Synchronisation and Quality agent is the platform's data steward. It governs the flow of data between the platform and every connected source system — ensuring that what the platform knows about projects, resources, finances, and risks accurately reflects what is recorded in the systems of record, and that the quality of that data meets the standards required for reliable analytics and decision-making.

Without this agent, the platform's value depends on the quality of data integration happening correctly and continuously. With it, data synchronisation is governed, monitored, and quality-assured — and the platform can be trusted to reflect the real state of the enterprise's projects.

---

## What It Does

**It orchestrates data synchronisation from connected systems.** The agent manages scheduled and triggered synchronisation jobs that pull data from connected source systems — Planview, SAP, Jira, Workday, and other connected platforms — and load it into the platform's canonical data model. Each sync job is configured with a source connector, a mapping definition, a quality threshold, and a conflict resolution strategy.

**It validates data against canonical schemas.** Every record ingested from a source system is validated against the platform's canonical schema for that entity type. The validation checks that required fields are present, that values are of the correct type and within acceptable ranges, and that relationships between entities are consistent. Records that fail validation are quarantined, the failure reason is recorded, and an alert is raised so that the issue can be investigated and resolved.

**It applies field and entity mapping.** Source systems rarely organise their data in the same way as the platform's canonical model. The agent applies configurable mapping rules that translate each source system's field names, data types, and value conventions into the platform's standard format. This mapping is defined in mapping rule files that can be updated without code changes when source systems change their data structures.

**It detects and resolves conflicts.** When the same entity appears differently in two connected sources — for example, a project's end date recorded differently in Planview and Jira — the agent detects the conflict and applies a configured resolution strategy: last-write-wins (the most recent update prevails), timestamp-based (the most recently modified record prevails), authoritative-source (one system is designated as the source of truth), prefer-existing (keep the platform's current value), or manual (flag the conflict for human resolution). The chosen strategy is configurable per entity type and per connector.

**It detects and merges duplicate records.** When the same real-world entity has been created multiple times — the same project appearing as two records, the same vendor registered twice — the agent uses fuzzy matching (with rapidfuzz) to identify likely duplicates and either merges them automatically or flags them for manual review. This prevents the fragmentation and inconsistency that accumulates when integration issues are not actively managed.

**It maintains data quality metrics.** For every data domain, the agent calculates quality scores across multiple dimensions: completeness (are required fields populated?), consistency (do related records agree?), timeliness (how recently was the data updated?), uniqueness (are there duplicate records?), schema compliance (does the data conform to the defined schema?), and auditability (is the lineage of each record traceable?). These scores are surfaced in the data quality dashboard.

**It manages the retry queue.** When a synchronisation job fails — because a source system is unavailable, or a record fails validation — the agent adds the failed record to a retry queue and reattempts the synchronisation after a configured delay. Failed records that cannot be resolved automatically are escalated for manual investigation.

**It emits data quality events.** Sync completions, quality threshold breaches, conflict detections, and duplicate identifications are all published as events on the platform's event bus, allowing other agents and monitoring systems to respond to data quality issues as they arise.

---

## How It Works

The agent is built around a set of connector-specific synchronisation pipelines, each defined by a manifest that specifies the source connector, the entity types being synced, the mapping rules, the quality thresholds, and the conflict resolution strategy. These pipelines are orchestrated by the agent on a configured schedule or triggered by events. Azure Data Factory is used for batch synchronisation; Azure Event Grid and Service Bus handle event-driven updates. Azure Key Vault manages the credentials needed to connect to each source system, accessed through a task-local secret context that prevents credential leakage.

The agent uses rapidfuzz for fuzzy matching in duplicate detection, providing probabilistic similarity scores rather than exact-match only.

---

## What It Uses

- Connector integrations: Planview, SAP, Jira, Workday (and all other connected systems)
- Mapping rule definitions for each connector and entity type
- Quality threshold rules per entity type and quality dimension
- Conflict resolution strategy definitions
- Azure Data Factory for batch ETL
- Azure Event Grid and Service Bus for event-driven sync
- Azure Key Vault for credential management
- Azure Cosmos DB and SQL for data storage
- Azure Log Analytics for sync monitoring and telemetry
- rapidfuzz for duplicate detection via fuzzy matching
- Agent 22 — Analytics and Insights for data quality reporting

---

## What It Produces

- **Synchronised data**: validated, mapped, quality-checked records loaded into the platform's canonical data store
- **Validation failure records**: quarantined records with detailed failure reasons
- **Conflict resolution records**: documentation of every conflict detected and how it was resolved
- **Duplicate detection reports**: identified duplicate records with similarity scores and resolution outcomes
- **Data quality scores**: per-entity, per-dimension quality metrics maintained as time series
- **Retry queue**: tracked list of failed sync records with retry status
- **Sync telemetry**: timing, volume, and success rate metrics for every sync job
- **Data quality dashboard**: real-time view of overall data quality posture across all connected systems
- **Data quality alerts**: notifications when quality scores fall below configured thresholds

---

## How It Appears in the Platform

The data quality picture is accessible from the **Connector Marketplace** in the administration console, where each connector's sync status, last sync time, success rate, and quality scores are displayed. Detailed data quality metrics are available in the **Dashboard Canvas** through a dedicated data quality panel.

Sync failures and quality alerts surface in the platform's **Notification Centre**, ensuring that data quality issues are visible to the teams responsible for resolving them. The retry queue can be managed from the connector detail view.

The assistant panel supports data quality queries: "When was the SAP data last synchronised?" "Are there any unresolved data conflicts?" "What is the current data quality score for project entities?"

---

## The Value It Adds

The value of the platform's analytics, reporting, and decision support capabilities depends entirely on the quality and currency of the underlying data. If the data is stale, incomplete, or inconsistent, every dashboard, every forecast, and every recommendation built on it is unreliable. The Data Synchronisation and Quality agent protects the data foundation that makes everything else trustworthy.

For organisations that have invested in multiple PPM, ERP, and collaboration systems, the data fragmentation problem is significant. Data about the same project may be held in three or four different systems, with no single source of truth. This agent resolves that fragmentation — maintaining a single, high-quality, continuously synchronised canonical record that all platform capabilities can depend on.

---

## How It Connects to Other Agents

The Data Synchronisation and Quality agent is a foundational service that supports every other agent in the platform by maintaining the data quality of the shared data store. It publishes quality metrics to **Agent 22 — Analytics and Insights** for reporting. Quality threshold breaches may trigger remediation workflows managed by **Agent 24 — Workflow Process Engine**. Lineage data maintained by this agent supports the compliance evidence managed by **Agent 16 — Compliance and Regulatory**.
