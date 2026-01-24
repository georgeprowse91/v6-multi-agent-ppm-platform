# Data Architecture

## Introduction

The Multi‑Agent PPM Platform relies on a robust data architecture to store, manage and disseminate information across agents, connectors and user interfaces. This architecture balances consistency with performance and enables governance, auditability and analytics. The design follows modern best practices: event‑driven data propagation, clearly defined ownership, strong data standards, scalable storage layers and a comprehensive quality framework.

## Data Ownership Model

The platform adopts a domain‑driven data ownership model: each agent is the system of record for its domain entities. For example, the Demand & Intake agent owns Idea and Proposal objects; the Business Case agent owns BusinessCase and associated financial models; the Portfolio Strategy agent owns Portfolio, Scenario and AlignmentScore records; the Program Management agent owns Program and ProgramDependency; the Project Definition agent owns Project, Charter, Requirement, WBSItem; and so on. This pattern ensures that:

Each entity has a single authoritative owner responsible for CRUD operations and enforcing business rules.

Other agents act as secondary readers, accessing data via APIs or events but not modifying the canonical record.

Ownership boundaries align with the agent specifications (see /agent_specs).

The data ownership table lists each entity, the owning agent and secondary users. For example, Resource data is owned by the Resource & Capacity agent, with secondary access by Schedule & Planning (for allocation), Portfolio Strategy (for optimisation) and Financial Management (for cost rates). Risk objects are owned by the Risk Management agent but consumed by Program Management, Portfolio Strategy and Reporting & Insights. This explicit mapping supports governance and clarifies responsibilities.

## Universal Data Standards

To promote consistency across agents and connectors, the architecture defines universal standards applied to all domain entities:

Identifiers – Primary keys use UUID v4 or human‑readable codes with prefixes (e.g., PROJ-1234, RISK-5678). IDs are immutable and never reused.

Timestamps – All date/time fields use ISO 8601 format in UTC (e.g., 2026-01-20T14:30:00Z). Each record includes createdAt, updatedAt and optional validFrom/validTo for temporal versions.

Enumerations & Status Fields – Common enumerations are standardised across modules: project status (e.g., Proposed, Approved, In Progress, Completed, On Hold, Cancelled); task status; risk status; approval status. Custom statuses are allowed but must map to canonical categories.

Currency & Units – Monetary values include ISO 4217 currency codes. Quantities specify units (e.g., hours, person‑days, USD) to avoid ambiguity. Multi‑currency fields support conversion using daily rates.

Versioning – Baselines (scope, schedule, budget) use semantic version numbers (e.g., 1.0.0, 1.1.0) and support snapshots. Changes are recorded in the audit log.

Audit Fields – All entities include audit fields capturing the user who created or modified the record, timestamps, and context (agent, API or UI). These audit logs feed into compliance reporting.

## Data Flow Patterns

Data propagation follows three canonical patterns:

Event‑Driven Propagation – Agents publish domain events (e.g., ProjectCreated, RiskMitigated) to a central event bus. Subscribers (other agents, connectors, analytics pipeline) consume these events to update their own state. This pattern promotes loose coupling and near real‑time synchronisation.

API‑Based Retrieval – When immediate data consistency is required (e.g., a user viewing the latest risk register), agents call each other’s APIs to fetch data. The API gateway handles authentication and routing. Caching may be used to improve performance, but the source of truth remains with the owning agent.

Cache‑Aside Strategy – To reduce latency and offload read traffic, commonly accessed data is cached in Redis. Agents retrieve from the cache first and populate it on cache miss. TTL values and event‑driven invalidation ensure that stale data is refreshed.

## Data Storage Architecture

The storage architecture comprises multiple layers:

Operational Data Store (ODS) – A relational database (PostgreSQL or Azure SQL Database) stores canonical domain data. Tables are partitioned by tenant and by time where appropriate (e.g., tasks partitioned by project or month). Indexing strategies support fast queries on IDs, foreign keys and timestamp ranges.

Event Store – An append‑only log persisted in a separate database or messaging system captures all domain events. Each event record contains a timestamp, event type, payload and version. Events support rebuilding materialised views and provide an immutable audit trail.

Analytics Data Platform – A columnar data warehouse (e.g., Snowflake, Databricks) hosts a star schema with fact tables (e.g., FactProject, FactTask, FactCost) and dimension tables (e.g., DimDate, DimPortfolio, DimResource). Data is loaded from the ODS and event store every 15 minutes via ETL or ELT processes. The warehouse supports slowly changing dimensions and historical analysis.

Cache Layer – A distributed cache (Redis or Azure Cache for Redis) holds reference data (project lists, user profiles) and computed results. Cache entries have TTLs and are invalidated when corresponding events occur.

Document Store – An object storage (Azure Blob Storage) or document database (MongoDB) stores unstructured files (charters, contracts, reports). Metadata is stored in the ODS for indexing and retrieval.

### Partitioning, Replication & Backup

Data is partitioned by tenant to ensure isolation in multi‑tenant SaaS deployments. Within each tenant, large tables (e.g., task logs, audit logs) may be partitioned by date. Replication across availability zones ensures high availability. Daily backups of the ODS and event store are retained for 30 days, while weekly and monthly backups support longer retention (up to seven years for compliance data). Caches are treated as disposable and rebuildable from source systems.

## Data Quality Framework

Maintaining data quality is essential for reliable AI and decision‑making. The architecture includes a Data Quality Framework with the following elements:

Validation Rules – Standardised rules verify referential integrity (e.g., project ID must exist), enforce business logic (e.g., budget cannot be negative), check completeness (required fields), and ensure consistency (e.g., status transitions follow allowed states). Validation occurs on write operations and during ETL processes.

Quality Metrics – The platform measures completeness, accuracy, consistency and timeliness of data. Dashboards display quality scores per entity and highlight problem areas. Thresholds trigger alerts when metrics fall below acceptable levels.

Automated Remediation – The Data Synchronisation agent monitors data quality and attempts to correct issues automatically (e.g., filling missing values from authoritative sources or rolling back invalid updates). When automatic remediation fails, it creates tasks for data stewards.

Root Cause Analysis – Data lineage capabilities track sources, transformations and consumers of data, enabling investigators to trace errors to their origin.

## Data Privacy & Compliance

The platform adheres to strict privacy and compliance requirements:

Classification Levels – Data is classified as Public, Internal, Confidential or Restricted. Confidential covers sensitive personal information (e.g., salaries, performance evaluations), while Restricted includes regulated data (e.g., financial statements, personally identifiable information). Classification dictates access controls, encryption requirements and retention policies.

GDPR & Privacy Rights – Users have rights to access, rectify, erase and export their data. The system must support data subject requests through self‑service portals or administrator workflows.

Retention Schedules – Different categories of data have prescribed retention periods. For example, audit logs and financial data must be retained for at least seven years; program and project records for five years after closure; personal data is deleted upon request unless retention is required by law.

Consent & Data Use – When storing personal data, the platform records consent and purpose. Data is only used for the specified purposes and shared with third parties under contractual obligations.

## Conclusion

The data architecture of the Multi‑Agent PPM Platform is designed to ensure integrity, consistency, performance and compliance. By defining clear ownership, adopting universal standards, employing event‑driven patterns, and implementing scalable storage and quality frameworks, the platform can support complex PPM workflows while delivering trustworthy data to stakeholders and AI agents alike.
