# Agent 11: Resource & Capacity Management Agent

## Purpose

The Resource & Capacity Management Agent (RCA) manages both the supply of resources (people, equipment, skills) and the demand from projects and programs. It is responsible for creating and maintaining a centralised resource pool, matching resource skills to project requirements, forecasting capacity and utilisation, and identifying allocation conflicts. By providing real‑time insights into availability, utilisation and skill gaps, it enables portfolio managers and PMO teams to make informed staffing decisions and optimise workload distribution.

## Key Capabilities

**Centralised resource pool:** maintain a master database of named resources and generic roles, including skills, certifications, locations, cost rates and calendars.

**Demand intake & approvals:** accept resource requests from project and program managers; route to appropriate managers for approval, rejection or negotiation.

**Skill matching & intelligent search:** match project requirements to available resources using skill tags, competency levels and historical performance. Support partial matches and recommend training or hiring to close gaps.

**Capacity planning & forecasting:** forecast future demand and supply based on project schedules, attrition trends and holiday calendars. Identify over‑allocations, under‑utilisation and capacity bottlenecks.

**Scenario modelling & what‑if analysis:** allow planners to model different staffing scenarios (e.g., adding headcount, shifting dates) and evaluate impacts on project timelines and utilisation.

**Role‑based vs. named assignments:** support planning at the role level during early stages and progressively assign named individuals as the schedule becomes firm.

**Cross‑project resource management:** track resource commitments across multiple projects and programs, enforce allocation thresholds and highlight competing demands.

**Integration with HR & timesheet systems:** synchronise employee details, availability and actual effort logged from HR and timesheet tools.

**Alerts & notifications:** notify stakeholders when resources become over‑allocated, when skill gaps remain unresolved or when approval deadlines approach.

## AI Technologies & Techniques

**Predictive capacity forecasting:** use time‑series models (e.g., ARIMA, Prophet or LSTM) trained on historical utilisation and demand patterns to predict future capacity requirements.

**Skill inference & classification:** apply natural language processing (NLP) to parse resumes, performance reviews and training records to infer skills and proficiency levels.

**Optimisation algorithms:** leverage heuristics, mixed‑integer programming or genetic algorithms to recommend optimal resource allocations considering constraints (skills, availability, costs, priorities).

**Anomaly detection:** detect unusual utilisation trends or over‑booking patterns using statistical outlier detection.

**Social network analysis:** identify informal networks and subject‑matter experts by analysing collaboration data (e.g., email/Teams interactions).

## Methodology Adaptation

**Agile:** support sprint‑level capacity planning (e.g., team velocity), track story points assigned to resources, and recommend sprint team compositions based on skills and velocity history.

**Waterfall:** plan resource usage across longer phases, emphasising critical path resource availability and role‑based assignments.

**Hybrid:** handle concurrent Agile sprints and Waterfall phases by maintaining a unified resource calendar and allocation rules.

## Dependencies & Interactions

The RCA interacts extensively with other agents:

**Schedule & Planning Agent (10):** consumes WBS and task durations to determine resource demand; returns allocation recommendations.

**Demand & Intake Agent (4):** receives resource requirements embedded in project requests.

**Program Management Agent (7):** supports cross‑project resource coordination within programs.

**Portfolio Strategy & Optimisation Agent (6):** provides capacity constraints for portfolio prioritisation.

**Financial Management Agent (12):** supplies cost rates and forecasts to financial planning.

**Change & Configuration Management Agent (17):** ensures resource assignments are updated upon approved changes.

## Integration Responsibilities

**Human Resources (HR) systems:** pull employee data (roles, skills, compensation, availability) from SAP SuccessFactors, Workday or Azure Active Directory.

**Timesheet & time‑tracking systems:** import actual hours from Planview Enterprise One, Azure DevOps or Jira Tempo to feed utilisation metrics.

**Learning management systems:** sync training completions and certifications.

**Calendar & leave management:** integrate with Outlook and HR calendars to capture planned leave and holidays.

Provide REST/GraphQL APIs for other agents and front‑end components to query availability, skills, and assignments.

## Data Ownership & Schemas

**Resource profiles:** ID, name, role, skills (tags), competencies, certifications, location, cost rates, calendar, team memberships.

**Capacity calendar:** mapping of resource availability by date and time, including planned leave and holidays.

**Allocations:** assignments of resources to tasks/projects/programs with start/end dates, allocation percentages and status.

**Demand requests:** records of resource requests, required skills, duration, requested dates and approval status.

**Utilisation metrics:** actual hours vs. planned hours, capacity vs. demand, and utilisation percentage by resource and role.

## Key Workflows & Use Cases

Resource request & approval:

A project manager submits a resource request specifying required roles, skills, start/end dates, and effort.

The RCA validates the request against available capacity and routes to line managers or resource owners for approval.

Approvers review recommended candidates, adjust allocations or propose alternatives. Once approved, the RCA updates the allocation plan and notifies the Schedule & Planning Agent.

Skill matching & assignment:

When a task requires a specific skill, the RCA searches the resource pool for qualified candidates using AI‑based skill matching and ranking.

The agent returns a ranked list of candidates with availability windows, cost rates and utilisation impacts.

The project manager selects a candidate, and the RCA creates an allocation record, updating capacity and notifying affected agents.

Capacity forecasting & balancing:

On a periodic basis, the agent forecasts capacity vs. demand for upcoming periods and identifies over‑ or under‑utilised resources.

It generates reports and dashboards for portfolio managers, highlighting bottlenecks and recommending mitigation actions (hire, train, reschedule, outsource).

Scenario analysis:

Portfolio managers use the UI to model scenarios such as adding a new project, delaying an existing one, or reallocating resources.

The agent recalculates utilisation, identifies conflicts and provides comparative metrics (e.g., average utilisation, cost impact) for decision‑making.

## UI / UX Design

The Resource & Capacity Management Agent provides both planner‑facing and manager‑facing interfaces within the PPM platform:

**Resource pool dashboard:** a tabular and card view of all resources, searchable by name, role, skill or location. Columns show current utilisation, upcoming assignments, certifications and cost rates. Users can drill into a resource profile for detailed history, skills and calendar.

**Capacity heatmap:** an interactive heatmap displaying utilisation percentages across resources and time (e.g., weeks). Over‑allocation is highlighted in red, under‑utilisation in blue. Filters allow sorting by team, role or project.

**Resource request form:** an embedded form that project managers use to request resources; includes pickers for skills, roles, dates and estimated effort. The agent provides real‑time availability suggestions and alternative dates.

**Scenario modelling canvas:** a side‑by‑side comparison tool enabling portfolio managers to create scenarios by adjusting project dates or adding/removing resources. The agent recalculates metrics and displays differences.

**Notifications & approvals:** integration with the Approval Workflow Agent to display approval tasks in the user’s workspace, with quick actions (approve, reject, modify).

**Integration with the Orchestration Layer:** When a user interacts with the resource dashboard, the Intent Router passes the query to the RCA. The Response Orchestration agent coordinates calls to the RCA, Schedule & Planning agent, and Financial agent (for cost data), assembles a consolidated response and returns to the UI.

## Configuration Parameters & Environment

**Max allocation threshold:** default maximum utilisation (e.g., 100 %). Configurable per role or resource.

**Skill taxonomy:** a configurable ontology of skills, certification levels and categories. Maintained via the Template & Methodology agent.

**Forecast horizon:** number of months into the future to forecast capacity (default: 12 months).

**Approval routing rules:** mapping of resource types to approving managers (e.g., design resources require design manager approval).

**Integration endpoints:** URLs and authentication settings for HR, timesheet and calendar systems.

### Azure Implementation Guidance

Assuming an Azure‑centric architecture:

**Data storage:** Use Azure SQL Database or Azure Cosmos DB for structured resource profiles, allocations and requests. Azure Blob Storage can store unstructured resumes or training documents.

**API hosting & orchestration:** Implement the RCA as a microservice using Azure Functions or Azure App Service. Use Azure API Management to expose REST/GraphQL endpoints to other agents and UIs. Inter‑agent communication occurs via Azure Service Bus topics and queues.

**Machine learning:** Deploy forecasting and optimisation models using Azure Machine Learning; register models in an ML registry, orchestrate retraining pipelines and monitor drift. Use Azure Cognitive Search with semantic search for skill matching.

**Integration:** Connect to HR and timesheet systems via Azure Logic Apps or Azure Data Factory with prebuilt connectors (e.g., Workday, SAP). Use Microsoft Graph API to fetch calendar data from Outlook.

**Security:** Enforce role‑based access via Azure AD groups and managed identities. Sensitive data such as cost rates must be encrypted at rest using Azure Key Vault for key management.

**Scalability:** Use Azure Kubernetes Service (AKS) or serverless premium plans to scale microservices horizontally based on message queue length or CPU usage.

## Security & Compliance Considerations

**Data protection:** encrypt personal and salary data in storage and transit. Apply data masking when exposing resource information to users without cost visibility.

**Access control:** enforce principle of least privilege; only authorised users can view or modify allocations. Use policies to restrict access to sensitive HR data.

**Audit logging:** log all requests, approvals and allocation changes with user IDs and timestamps. Integrate logs with Azure Monitor and export to Log Analytics for auditing.

**Compliance frameworks:** support GDPR (right to be forgotten) by enabling deletion/anonymisation of resource profiles; maintain separation of duties for approvals.

## Performance & Scalability

**Real‑time responses:** ensure sub‑second performance for search queries and capacity lookups by leveraging cached indexes in Azure Redis Cache.

**Batch processing:** offload forecasting and optimisation computations to background jobs triggered by Azure Functions or Data Factory; schedule outside of peak hours.

**High availability:** deploy services across multiple availability zones; design for zero‑downtime rolling upgrades via AKS or App Service deployment slots.

## Logging & Monitoring

Instrument API calls with Application Insights to monitor latency, throughput and error rates.

Emit custom metrics (e.g., average utilisation, number of pending requests) to Azure Monitor.

Configure alerts for thresholds such as over‑allocation counts or forecast errors; integrate with notification channels (Teams, email).

## Testing & Quality Assurance

Create unit tests for allocation algorithms, skill matching logic and forecasting models.

Use synthetic test data to verify performance at scale (e.g., 10k resources, 1k projects).

Conduct user acceptance testing with representative PMO users; validate UI flows, approval processes and scenario modelling.

## Notes & Further Enhancements

Consider integrating external freelance marketplaces (e.g., Upwork) to source additional capacity for short‑term needs.

Provide career development recommendations to resource managers by analysing training needs and high‑demand skills.
