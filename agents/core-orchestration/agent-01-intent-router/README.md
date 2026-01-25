# Agent 1: Intent Router Agent Specification

## Purpose

The Intent Router Agent is the front‑door of the multi‑agent PPM platform. It analyzes every natural language request sent by a user through the assistant or UI and determines which downstream domain agents should process the request. By performing intent classification, entity extraction and routing decisions, it ensures the right agents are invoked in the correct order and with the right context.

## Key Capabilities

**Multi‑intent detection:** Identifies one or more intents within a single user request and maintains session context (e.g., “Show me Apollo’s schedule and flag any budget risks”).

**Context extraction:** Uses conversation history to infer implicit parameters (project names, methodologies) and fill missing data.

**Disambiguation and clarification:** Detects ambiguous requests and prompts the user for clarification (e.g., asking which project or what type of schedule update).

**Routing prioritization:** Prioritizes requests based on user role, urgency and complexity and forwards them to the Response Orchestration Agent.

**Session state management:** Maintains conversational state across turns and stores user preferences and classification history.

**Fallback handling:** Provides human‑readable fallback responses and clarifications for out‑of‑scope or low‑confidence intents.

## AI Technologies

Azure OpenAI Service for large‑language‑model‑based intent classification and named entity recognition (fine‑tuned on PPM domain data).

Azure Language Understanding (CLU) for contextual embeddings and similarity matching.

Azure Cognitive Search for retrieving historical classifications and improving suggestions.

**Confidence scoring:** Statistical models to score classification confidence; triggers clarification when below threshold.

## Methodology Adaptations

The agent adjusts vocabulary and suggested next actions based on the selected project methodology:

**Agile:** Understands sprint terminology (burndown, velocity, user story points) and suggests sprint‑specific actions.

**Waterfall:** Recognizes phase‑gate terminology (baseline, critical path, earned value) and suggests phase‑specific actions.

**Hybrid:** Uses a combination of the above and defers ambiguous terms to the user.

## Dependencies & Interactions

**Response Orchestration Agent (Agent 2):** Receives a routing payload containing the classified intents, target agents, execution order and metadata.

**User Profile Service:** Queries for user role, permissions and active projects to refine classification.

**Project Lifecycle Agent (Agent 9):** Uses methodology selection data to adjust classification.

## Integration Responsibilities

Exposes a REST/GraphQL API endpoint for the web/mobile UI and assistant clients to send free‑text requests.

Publishes classification events to Azure Service Bus or Event Grid for consumption by the Response Orchestration Agent.

Interfaces with Azure AD for authentication and user context lookup.

## Data Ownership

**Session state:** Current conversation context (active project, methodology).

**Intent history:** Records of classified intents and associated entities for analytics and model improvement.

**User preferences:** Preferred terminology, response formats and disambiguation choices.

## Key Workflows

**Simple Query Routing:** The user asks a fact‑based question (“What’s the budget for Project Apollo?”). The agent classifies the intent (e.g., query.project.budget), extracts entities (Project = “Apollo”) and forwards the request to the Response Orchestration Agent with the target of the Financial Management Agent.

**Multi‑Intent Request:** The user asks for multiple pieces of information (“Show me Apollo’s schedule and flag budget risks”). The agent detects both schedule and risk intents and packages them into a compound routing payload for parallel execution.

**Ambiguous Request:** The user provides insufficient data (“Update the schedule”). The agent prompts the user to specify the project and the type of update.

## UI/UX Design

**Assistant Input Box:** All free‑text user inputs from the assistant panel are first processed by this agent. The UI displays helper prompt text like “Ask me about budgets, risks, or schedules…” and auto‑completes suggestions.

**Clarification Chips:** When a request is ambiguous, the agent returns quick‑action chips (e.g., list of projects, update options) displayed below the chat input, allowing the user to click to disambiguate.

**Confidence Indicators:** The UI may display a subtle “uncertain” badge when classification confidence is low, prompting users to rephrase.

**Auditing Pane:** Within project settings, admins can review historical intents and how they were routed to troubleshoot training.

## Configuration Parameters

**Classification Confidence Threshold:** Default 0.75; below this, the agent asks for clarification.

**Disambiguation Timeout:** Default 15 seconds; time the agent waits for user clarification before re‑prompting.

**Max Parallel Intents:** Default 3; maximum number of concurrent intents to avoid overloading downstream agents.

**Language Support:** List of supported languages/locales; default [“en‑US”].

**Caching Time‑to‑Live:** Duration (in minutes) to cache classification results; default 10 minutes.

## Azure Implementation Guidance

**Compute:** Deploy the agent as an Azure Function (HTTP trigger) written in Python or C# for stateless classification. Use Durable Functions if extended conversational state is required.

**AI Services:** Integrate with Azure OpenAI for LLM calls and Language Understanding (CLU) for intent classification. Use Azure Cognitive Search for historical query retrieval.

**State Management:** Store session and intent history in Azure Cosmos DB (NoSQL) or Azure Table Storage. Use Redis Cache for transient conversation context.

**Messaging:** Use Azure Service Bus or Event Grid to publish routing events to downstream agents.

**Authentication:** Rely on Azure Active Directory for token-based authentication and to retrieve user profiles.

**Monitoring:** Use Application Insights to track classification latency, error rates and model confidence scores. Set up alerts for classification errors.

## Security & Compliance

All API endpoints require OAuth2 tokens issued by Azure AD.

Encrypt conversation state data at rest using Azure Storage encryption and in transit via HTTPS.

Maintain audit logs of user requests and routing decisions for compliance and troubleshooting.

Apply role-based access control (RBAC) to restrict who can view classification history and adjust thresholds.

## Performance & Scalability

The agent must handle high concurrency with low latency (< 300 ms per classification) by scaling Azure Functions using premium plan or Kubernetes‑based container instances.

Use asynchronous LLM calls and caching to minimise response times.

Implement circuit‑breaker patterns when downstream AI services degrade.

## Logging & Monitoring

Log raw user queries, classified intents, confidence scores and routing payloads to Application Insights.

Monitor call volumes, error rates and average latency. Use Azure Monitor dashboards to visualise trends.

Record metrics for ambiguous request frequency to guide improvements in training data.
