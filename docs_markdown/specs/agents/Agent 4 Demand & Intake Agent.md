# Agent 4: Demand & Intake Agent Specification

## Purpose

The Demand & Intake Agent captures incoming project requests, ideas and change initiatives from stakeholders and manages the demand pipeline. It provides a single funnel through which all opportunities enter the portfolio, automatically categorising, deduplicating and triaging requests. By structuring demand early, the agent enables informed investment decisions and portfolio planning.

## Key Capabilities

**Multi‑channel intake:** Accepts requests via email, web forms, Slack/Teams integrations and API submissions.

**Automatic categorisation:** Uses NLP to classify requests into categories (project, change request, issue, idea) and assess urgency and business unit.

**Duplicate detection:** Performs semantic similarity analysis to detect requests that describe the same need.

**Preliminary triage:** Screens requests for completeness and basic feasibility; flags missing information and requests clarifications.

**Pipeline visualisation:** Presents a Kanban or funnel view of demand stages (Received, Screening, Analysis, Approved, Rejected) for PMOs and executives.

**Requester communication:** Sends confirmation receipts, status updates and clarifies missing information via assistant messages or email.

**Methodology suggestion:** Based on request characteristics (e.g., size, complexity), suggests an appropriate project methodology (Agile vs. Waterfall).

## AI Technologies

**NLP classification:** Uses Azure OpenAI or Language Understanding (CLU) models to classify request types and extract key metadata (project names, business unit, urgency).

**Semantic similarity:** Embedding models (e.g., sentence transformers) and vector similarity search in Azure Cognitive Search to identify duplicates.

**Sentiment analysis:** Detects tone of requestors to prioritise urgent or frustrated users.

**Auto‑completion:** Suggests missing fields in intake forms based on extracted entities and past requests.

## Methodology Adaptations

The agent operates before a project has been initiated and therefore has no direct methodology dependency. However, it can recommend a methodology based on size, complexity and organisational context (e.g., “For small, fast‑moving initiatives, consider Agile”).

## Dependencies & Interactions

**Email & Messaging Systems:** Monitors a dedicated PMO inbox and Slack/Teams channels for incoming requests (via Azure Logic Apps connectors).

**Service Management Tools:** Connects to ServiceNow or similar tools for IT demand intake.

**CRM & Marketing Systems:** Integrates with Salesforce or Dynamics to import customer‑driven requests.

**User Profile Service:** Associates requests with requestor roles, departments and permissions.

**Portfolio Strategy Agent (Agent 6):** Sends screened requests for prioritization and scoring.

## Integration Responsibilities

Implements API endpoints and connectors to ingest data from email, web forms, Slack/Teams and external intake portals.

Publishes events (e.g., demand.created, demand.screened, demand.approved) to Service Bus/Event Grid for downstream agents.

Queries CRM/ERP systems for additional context (e.g., revenue data) when assessing requests.

## Data Ownership

**Demand repository:** Stores all intake requests, categories, metadata and status throughout the demand pipeline.

**Classification models & training data:** Maintains labelled data used to improve categorization and duplicate detection.

**Requester communication logs:** Records confirmation messages, clarification requests and status updates for each demand item.

## Key Workflows

**Request Capture:** A stakeholder submits a request via the web form or Slack. The agent extracts the project description, business unit, requested timeline and urgency. It acknowledges receipt and assigns a demand ID.

**Automatic Categorisation & Deduplication:** The agent classifies the request and searches for similar requests. If duplicates are found, it merges them or notifies the requester and relevant team to avoid redundancy.

**Preliminary Screening:** The agent checks whether essential information is provided (objectives, benefits, risks) and requests missing details. It may also reject obviously unaligned requests based on predefined criteria.

**Pipeline Management:** The request is added to the demand pipeline. PMO analysts can move it through stages via drag‑and‑drop or automation rules. The agent updates requestors on status changes.

**Methodology Recommendation:** For valid requests, the agent recommends a project methodology and forwards the item to the Business Case Agent (Agent 5) for further analysis.

## UI/UX Design

**Intake Form & Slack Bot:** Provides a dynamic web form with autofill suggestions and a Slack bot command (e.g., /newproject) to capture requests. The form supports attachments and required fields.

**Demand Pipeline Dashboard:** Displays all intake items as cards in stages, with filters by category, business unit and priority. Users can click a card to view details, classification results and duplicate links.

**Duplicate Alert UI:** Shows potential duplicates with similarity scores, allowing analysts to merge or link items.

**Request Status Feed:** Requestors receive updates via email or assistant messages; the assistant panel lists “My Requests” with statuses.

**Screening Modal:** Analysts can open a modal to review and edit request details, adjust classification and send clarifications.

## Configuration Parameters

**Similarity Threshold:** Default 0.85; similarity score above which requests are considered duplicates.

**Mandatory Fields:** List of fields required to proceed (e.g., business objective, benefits). Default includes objective, estimated budget.

**Auto‑Rejection Rules:** Configurable criteria to auto‑reject requests (e.g., incomplete data, off‑strategy categories).

**Notification Preferences:** Determines channels and frequency for requestor updates.

**Methodology Decision Rules:** Logic table mapping request characteristics (size, complexity, strategic alignment) to recommended methodologies.

## Azure Implementation Guidance

**Compute:** Use Azure Functions or Azure App Service to implement classification and intake APIs. Use Azure Logic Apps for multi‑channel triggers (email, forms, Slack/Teams connectors).

**AI Services:** Use Azure OpenAI Service or Azure Cognitive Services (Language Understanding, Text Analytics) for NLP classification, entity extraction, sentiment analysis and similarity search.

**Data Storage:** Store demand items and metadata in Azure Cosmos DB (for flexible schema and scale) or Azure SQL Database if relational structure is preferred.

**Search:** Use Azure Cognitive Search with vector search to store embeddings and perform duplicate detection.

**Messaging:** Publish demand events to Azure Service Bus or Event Grid for downstream processing.

**Integration:** Configure Logic Apps connectors for Outlook, Gmail, Slack, Teams and ServiceNow for inbound data and notifications.

**Authentication:** Use Azure AD B2E for employee authentication; assign RBAC roles for request submission and review.

**Monitoring:** Use Application Insights to track intake volumes, classification accuracy and duplicate detection rates; implement telemetry for failed ingestion events.

## Security & Compliance

Validate and sanitize all inbound request data to prevent injection attacks.

Enforce authentication and authorization on API endpoints; use application roles to restrict who can submit and review requests.

Encrypt demand data at rest and in transit.

Maintain audit trails of changes to demand items and classification results.

## Performance & Scalability

Design the intake pipeline to handle bursts of requests from multiple channels; use message queues to smooth peaks.

Cache frequently accessed classification results to reduce latency.

Scale up Azure Functions or App Service instances based on ingestion volume.

## Logging & Monitoring

Log incoming requests, classification outcomes, duplicate detection results and triage actions to Application Insights.

Monitor classification accuracy and adjust models as needed; collect labelled training data.

Set up alerts for ingestion failures, sudden spikes in request volume and duplicate detection errors.
