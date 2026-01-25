# Agent 2: Response Orchestration Agent Specification

## Purpose

The Response Orchestration Agent acts as the coordinator for multi‑agent queries. After receiving a routing payload from the Intent Router Agent, it determines which domain agents to invoke, plans the execution order (parallel or sequential), manages dependencies and aggregates responses into a coherent output for the user. It ensures that complex requests involving multiple data sources are handled efficiently and transparently.

## Key Capabilities

**Multi‑agent query planning:** Builds a dependency graph of target agents and determines optimal execution strategy (parallel when independent, sequential when outputs feed into subsequent agents).

**Parallel and sequential execution:** Invokes agents concurrently or in series depending on dependencies; handles partial responses when some agents fail.

**Response aggregation:** Merges and reconciles responses using conflict resolution and summarization, presenting a unified answer to the user.

**Timeout and fallback management:** Sets timeouts for agent responses and uses fallback strategies when agents are unavailable or return errors.

**Result caching:** Stores results of frequently requested queries to avoid redundant calls and improve performance.

**Quality control:** Monitors agent performance metrics (latency, error rates) and applies circuit breaker patterns when thresholds are exceeded.

## AI Technologies

**Dependency graph analysis:** Custom algorithms determine dependencies between agents based on query types and known data flows.

**Azure OpenAI for summarization:** Uses LLMs to combine outputs from multiple agents into human‑readable narratives.

**Anomaly detection:** Machine learning models flag contradictory information from different agents and prompt for reconciliation.

**Relevance ranking:** Scores and prioritizes response components to surface the most important information to the user.

## Methodology Adaptations

**Agile Projects:** Prioritises sprint‑level data when constructing dashboards and responses; emphasises burndown charts and velocity metrics.

**Waterfall Projects:** Focuses on phase completion status, critical path and baseline variances when aggregating information.

**Hybrid Projects:** Combines both sets of metrics and formats output accordingly.

## Dependencies & Interactions

**Intent Router Agent (Agent 1):** Receives routing payload and returns aggregated responses.

**Domain Agents (e.g., Financial, Risk, Schedule, Project Definition):** Invoked via REST/GraphQL endpoints; orchestrator manages concurrency and dependency ordering.

**Message Bus (Azure Service Bus/Event Grid):** Subscribes to agent completion events for asynchronous workflows.

**Cache Service:** Reads/writes to a shared cache (Redis) to store recent query results.

## Integration Responsibilities

Calls domain agents synchronously via HTTPS or asynchronously via message bus.

Publishes aggregated results back to the assistant and UI clients via API or real‑time notification (SignalR, WebSockets).

Implements circuit breaker pattern to isolate failing agents.

Utilises Redis or Azure Cache for results caching.

## Data Ownership

**Query execution plans:** The dependency graphs and execution metadata for each request.

**Response cache:** Key‑value store of recent query results indexed by query signature.

**Agent performance metrics:** Response time, error rate and success/failure counts per agent to support quality control.

## Key Workflows

**Parallel Agent Invocation:** For a dashboard query (“Show me Project Apollo health dashboard”), the orchestrator identifies required agents (Schedule, Risk, Financial, Project Definition, Reporting), invokes them in parallel and merges outputs into a consolidated dashboard.

**Sequential Agent Invocation:** For requests where one agent depends on another’s output (e.g., generate cost forecast after retrieving resource allocations), the orchestrator waits for the upstream agent to finish before calling the next.

**Partial Response Handling:** If some agents fail or exceed timeout thresholds, the orchestrator returns partial results and notifies the user which data is missing or delayed.

**Caching & Repeat Queries:** When a query matches a recent query signature, the orchestrator serves the cached result (if within TTL) to improve responsiveness.

## UI/UX Design

**Unified Answer Presentation:** The user receives a single response in the assistant panel or dashboard canvas. Data from multiple agents is collated and summarised; charts and tables are grouped logically.

**Real‑time Progress Indicators:** When executing long‑running multi‑agent queries, the UI displays a progress indicator showing which agents have responded and which are pending.

**Partial Results Notification:** If partial data is returned, the UI flags sections with “data unavailable” messages and offers to retry.

**Settings & History:** Administrators can view orchestration logs and cached query entries via a configuration page for troubleshooting.

## Configuration Parameters

**Max Concurrency:** Default 5; maximum number of agents invoked in parallel.

**Agent Timeout:** Default 30 seconds; time allowed for an agent to respond before fallback.

**Cache TTL:** Default 15 minutes; duration to store query results.

**Retry Attempts:** Default 1; number of retry attempts for failed agent calls.

**Fallback Policy:** Options (fail-fast, partial‑return, block) to determine behavior when critical agents fail.

## Azure Implementation Guidance

**Compute:** Implement the orchestrator as an Azure Durable Functions orchestrator function to support complex workflows, parallel fan‑out/fan‑in patterns and long‑running tasks.

**State Storage:** Use Azure Storage Blobs or Azure Cosmos DB as the state provider for Durable Functions. Use Redis Cache for response caching.

**Messaging:** Use Azure Service Bus or Event Grid to subscribe to domain agent events and to publish orchestrated responses.

**AI Services:** Use Azure OpenAI Service to summarise and synthesise aggregated responses.

**Monitoring:** Configure Application Insights and Durable Task framework instrumentation to trace orchestrations, track failures and measure latency.

**Resilience:** Implement circuit‑breaker and retry policies using the Polly library (for .NET) or built‑in Durable Functions patterns. Use Azure Key Vault to manage secrets for downstream agent APIs.

## Security & Compliance

The orchestrator must verify authorization for each sub‑request before invoking domain agents (using roles/permissions from Azure AD).

Ensure all data transmissions are over HTTPS; use managed identities for inter‑service communication.

Maintain audit logs of agent invocations and aggregated responses.

Cleanse sensitive data before caching results and define appropriate cache expiration rules.

## Performance & Scalability

Scale out Durable Functions workers based on throughput; consider using Premium Plan or App Service Environment for predictable capacity.

Tune concurrency limits and timeouts based on observed agent performance metrics.

Use caching and partial returns to reduce load and improve user experience.

## Logging & Monitoring

Record orchestration traces, agent invocation times, errors and fallback events in Application Insights.

Create dashboards (Azure Monitor Workbook) to track concurrency, latency and success rates by agent.

Set up alert rules for high error rates or long orchestration durations.
