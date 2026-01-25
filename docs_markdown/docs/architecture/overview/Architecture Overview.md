# Architecture Overview

## Introduction

The Multi‑Agent PPM Platform is built upon a modular, layered architecture that enables agility, scalability and extensibility. Rather than being a monolithic application, it comprises loosely coupled services connected via event‑driven and API‑based patterns. The architecture ensures that user experience, orchestration logic, domain intelligence, integration, data storage and security concerns are separated but operate cohesively. This overview provides a textual description of the architecture and explains how the major layers and components interact.

## Logical Layers

### 1. User Interface (UI) Layer

The UI layer delivers the web‑based experience to end users. It is responsible for rendering the methodology map, interactive canvas and dashboards. Key features include:

**Methodology Navigation:** The left panel displays the methodology map (phases or sprints) and lets users navigate to tasks and stage‑gates.

**Central Canvas:** The middle area shows work artefacts (charters, WBS, schedules, reports) and allows drag‑and‑drop editing.

**Right Sidebar/Assistant:** The right panel hosts the AI assistant chat and contextual insights, enabling conversational interaction with agents.

The UI is built as a single‑page application using modern web frameworks (e.g., React, TypeScript) and communicates with back‑end services via GraphQL and REST APIs. It implements role‑based access controls and supports responsive design to work across desktops and tablets.

### 2. Orchestration & Agents Layer

This layer comprises the brain of the platform. It includes the Intent Router and Response Orchestration agents that interpret user input, decide which domain agents to call and aggregate results. Domain agents implement specific business capabilities (e.g., Demand & Intake, Business Case, Portfolio Optimisation, Program Management, etc.). Each agent encapsulates its own logic, integration calls and data management. Agents are stateless by design, relying on the data layer for persistence and using message queues (e.g., Azure Service Bus, Kafka) to communicate.

Agents follow the principles outlined in the architecture document: they own their integrations, expose APIs for other agents, and publish events when data changes. The orchestrator coordinates multi‑agent workflows and ensures responses are returned in the correct order. Agents can be added, removed or replaced without impacting others, promoting extensibility.

### 3. Integration & Data Layer

This layer handles connectivity to external systems and manages all persistent data. It consists of:

**Connector Marketplace:** A set of reusable connector services for Planview, Jira, SAP, Workday, ServiceNow, Slack, Teams, and others. Connectors encapsulate authentication, API calls, data mapping and error handling. They support bi‑directional synchronisation, event‑driven updates, and graceful degradation when endpoints are unavailable.

**API Gateway:** An entry point that provides authentication, rate limiting, logging, protocol translation (GraphQL ↔ REST/OData), and circuit breaking. It routes requests to agents or connectors and captures metrics.

**Message & Event Infrastructure:** A combination of message queues and event streams (e.g., Azure Event Hubs, Kafka) used for decoupling components and enabling event‑driven architectures. Events represent changes in domain entities and trigger downstream processing.

**Operational Data Store (ODS):** A PostgreSQL or Azure SQL database that stores operational data for projects, programs, portfolios, risks, issues, resources, budgets and other entities. It follows a normalised schema with partitioning and indexing strategies for high‑volume transactions.

**Event Store:** An append‑only log that records domain events. It supports auditability, temporal queries and replay of events for rebuilding state or integrating new consumers.

**Analytics Data Platform:** A star‑schema data warehouse (e.g., Snowflake, Databricks) that ingests data every 15 minutes from the ODS and event store for reporting and analysis. It supports slowly changing dimensions (SCD‑Type 2) and can integrate with BI tools.

**Cache Layer:** A distributed cache (e.g., Redis) used to store frequently accessed reference data and query results, reducing load on primary databases. The cache uses TTL and event‑driven invalidation patterns to ensure consistency.

**Document Store:** An optional object storage (e.g., Azure Blob Storage) or NoSQL store (e.g., MongoDB) used to store unstructured documents, attachments and large artefacts.

## Security Boundaries

Security spans all layers. Key elements include:

**Identity & Access Management:** The platform integrates with enterprise identity providers (e.g., Azure AD, Okta) using SAML or OAuth to provide single sign‑on. Mutual TLS (mTLS) secures agent‑to‑agent communication, and secrets (API keys, tokens) are managed in a central vault.

**Role‑Based Access Control (RBAC):** A fine‑grained permission model defines roles (e.g., PMO Director, Project Manager, Resource Manager, Finance Controller) and entitlements. Row‑level and field‑level security enforce data segregation across business units and project classifications【565999142788795†L6484-L6853】.

**Encryption:** All data in transit uses TLS 1.3; data at rest is encrypted using AES‑256. Disk‑level encryption is enabled for databases, caches and storage. Keys are rotated regularly.

**Network Segmentation:** The architecture is divided into DMZ, application and data tiers. Firewalls and web application firewalls (WAF) protect inbound traffic, while internal communication is restricted to necessary ports【565999142788795†L6484-L6853】.

**Audit & Monitoring:** All API calls and data access are logged in a structured format with timestamps, user IDs, IP addresses and action details. Logs are retained for at least seven years to meet compliance requirements. Alerts are triggered on anomalous activities.

## Interactions and Data Flow

### Event‑Driven Pattern

Whenever an agent changes data (e.g., a schedule update, a new risk or an approved business case), it publishes a domain event to the event stream. Other agents or connectors subscribe to these events to react accordingly. For example, when the Resource Management agent assigns a resource to a task, it publishes a ResourceAssigned event. The Integration layer may then sync this update to Workday, while the Schedule agent updates calendars. This decouples agents and ensures eventual consistency.

### API‑Based Pattern

In scenarios where real‑time or on‑demand data retrieval is needed (e.g., a user viewing the latest project status), agents invoke APIs on other agents or connectors. The API gateway authenticates and routes these requests, and a caching layer may serve responses to reduce latency. Agents always consult the source of truth for authoritative data and only use cache for read optimisation.

### Cache‑Aside Pattern

The platform employs a cache‑aside strategy: when an agent retrieves data, it first checks the cache. If the data is not present, it fetches from the ODS or external system, stores it in cache and returns the result. Events or TTL expiration invalidate stale cache entries. This pattern improves performance while avoiding stale data.

## Scalability & Deployment Models

The platform is designed to scale horizontally. Each agent and connector can be deployed as a container or serverless function and scaled independently. The orchestrator distributes workload across available instances, and load balancers route incoming requests. High availability is achieved through multiple replicas and failover strategies. Deployment models include:

**Managed SaaS:** Hosted by the platform provider in a multi‑tenant environment. Customers access the platform via secure web access. Data is segregated by tenant using logical isolation and RBAC.

**Private Cloud:** Deployed within a customer’s private cloud subscription (e.g., Azure, AWS). Customers maintain control over data, network and security settings while benefiting from automation and updates.

**On‑Premises:** For organisations with strict data residency or compliance requirements, the platform can be installed in on‑premises environments. Components run on Kubernetes clusters or virtual machines, and connectors are configured to access internal systems.

CI/CD pipelines automate build, test, security scanning and deployment to each environment. Releases follow staged deployments (development → test → staging → production) and support blue/green strategies for zero‑downtime upgrades.

## Conclusion

The Multi‑Agent PPM Platform architecture is intentionally modular and layered. It enables organisations to adopt powerful AI‑driven PPM capabilities while integrating with existing systems and maintaining robust security. By separating user experience, orchestration, domain logic, integration and data storage, the platform can evolve quickly, scale efficiently and adapt to different deployment models. Security and observability are woven throughout, providing confidence in compliance and operational excellence.
