# Agent 21: Stakeholder Comms Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 21: Stakeholder Comms. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

Agent 21 owns stakeholder communication operations, including:

- Maintaining the stakeholder register and engagement profiles.
- Classifying stakeholders (influence/interest) and recommending engagement strategies.
- Building communication plans tied to portfolio/project updates.
- Generating, editing, scheduling, and sending outbound messages (email/Teams/Slack/SMS/push/portal).
- Collecting feedback and sentiment, tracking engagement, and producing comms reports.
- Coordinating events/meetings and publishing comms events to workflow/analytics systems.

Out of scope:

- Approving outbound communications (handled by Agent 03).
- Authoring/curating official knowledge artifacts (handled by Agent 19).
- Portfolio governance decisions or delivery lifecycle approvals (handled by other agents).

## Inputs and outputs

### Primary inputs (by action)

- `register_stakeholder`: `stakeholder` payload with name, email, role, organization, preferences.
- `classify_stakeholder`: `stakeholder_id`.
- `create_communication_plan`: `plan` payload with project, stakeholders, schedule, channel.
- `generate_message` / `edit_message`: message template data, attachments, recipients.
- `send_message` / `schedule_message`: `message_id` and delivery mode.
- `summarize_report`: `report` content plus target role/locale.
- `update_communication_preferences`: `stakeholder_id` with preference updates.
- `collect_feedback` / `analyze_sentiment`: feedback payloads or stakeholder identifier.
- `schedule_event`: event payload (time, attendees, meeting details).
- `track_engagement` / `track_delivery_event`: stakeholder and delivery telemetry.
- `get_stakeholder_dashboard` / `generate_communication_report`: project/filters.

### Outputs

- Stakeholder records, classifications, engagement strategies, and preferences.
- Communication plans, message drafts, delivery schedules, and send results.
- Feedback/sentiment results, engagement metrics, and reporting summaries.
- Workflow triggers, service bus events, and communication history entries.

## Decision responsibilities

Agent 21 is responsible for:

- Determining stakeholder classifications and engagement strategies.
- Selecting delivery channels based on preferences, consent, and channel availability.
- Scheduling batches/digests and optimizing send times.
- Generating and personalizing message content.
- Triggering workflow automation and publishing comms events/metrics.

Approval decisions and policy enforcement (beyond consent) remain with Agent 03.

## Must / must-not behaviors

Must:

- Enforce consent/opt-out rules before sending communications.
- Store communication history and emit comms events for downstream analytics.
- Respect delivery modes (immediate, scheduled, digest) and batching controls.
- Provide traceable outputs for stakeholder updates and message actions.

Must not:

- Send outbound communications requiring approval before Agent 03 approval is granted.
- Modify or overwrite authoritative knowledge documents owned by Agent 19.
- Exfiltrate or log secrets; use configured secret providers only.

## Overlap and handoff boundaries (Agents 19 & 03)

### Agent 03: Approval Workflow

**Overlap risk:** outbound communications that require approval or escalation.  
**Handoff:** Agent 21 submits message drafts + metadata to Agent 03 for approval when policy or content flags require it. Agent 21 resumes delivery only after approval status is returned.  
**Boundary:** Agent 03 owns approval decisions, audit trails, and approval notifications. Agent 21 owns message preparation, delivery execution, and delivery telemetry.

### Agent 19: Knowledge Document Management

**Overlap risk:** content summaries or reports that could become knowledge artifacts.  
**Handoff:** Agent 21 can request approved knowledge snippets or finalized documents from Agent 19 to use in communications; Agent 21 can submit post-communication summaries for capture.  
**Boundary:** Agent 19 manages canonical documents, versioning, and distribution repositories; Agent 21 only references or links those artifacts in outbound messages.

## Functional gaps, inconsistencies, and alignment needs

- **Approval enforcement:** current implementation flags `review_required` but does not block send; align with Agent 03 by adding a required approval state gate.
- **CRM alignment:** README lists Salesforce-specific variables while implementation supports generic CRM endpoints; document precedence and mapping.
- **Connector alignment:** Notification/Calendar integrations are used in code but not documented in required env vars; add connector configuration or defaults.
- **Templates/UI alignment:** communication templates and digest batching lack UI/portal configuration detail; define where templates live and how they are reviewed.
- **Telemetry alignment:** define how delivery events map to analytics (Agent 22/25) and knowledge capture (Agent 19).

## Communications trigger matrix (execution-ready)

| Trigger | Inputs | Action | Approval required | Output/records | Handoff |
| --- | --- | --- | --- | --- | --- |
| Stakeholder added | `stakeholder` payload | Register stakeholder + classify | No (unless policy) | Stakeholder profile, classification | Optionally send profile summary to Agent 19 |
| Project status update | `report`/summary source | Generate update message | Yes if external audience | Draft message, summary, delivery plan | Send draft to Agent 03 for approval |
| Risk/issue escalation | Risk payload + audience | Send escalation comms | Yes | Delivery results + history | Coordinate approvals with Agent 03 |
| Change request | Change details + audience | Compose change notice | Yes | Message + delivery telemetry | Agent 03 approval, Agent 19 update |
| Release milestone | Release notes | Broadcast release update | Yes if external | Message + schedule | Agent 03 approval; Agent 19 docs link |
| Stakeholder feedback received | Feedback payload | Analyze sentiment + update engagement | No | Sentiment score, engagement update | Feed analytics/knowledge |
| Event/meeting scheduled | Event details | Send invites/notifications | No (internal) | Calendar event, notifications | Calendar integration |
| Engagement drop | Engagement metrics | Trigger re-engagement plan | Maybe (policy) | New plan + draft message | Agent 03 approval if required |

## What's inside

- `agents/operations-management/agent-21-stakeholder-comms/src`: Implementation source for this component.
- `agents/operations-management/agent-21-stakeholder-comms/tests`: Test suites and fixtures.
- `agents/operations-management/agent-21-stakeholder-comms/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-21-stakeholder-comms --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/agent-21-stakeholder-comms/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### OAuth scopes (Microsoft Graph)

Ensure the Azure app registration includes the following scopes (delegated or application, depending on your deployment):

- `Mail.Send` (Exchange/Outlook email)
- `Calendars.ReadWrite` (meeting scheduling, invites, availability)
- `OnlineMeetings.ReadWrite` (Teams meeting links)
- `Chat.ReadWrite` or `ChannelMessage.Send` (Teams messaging)
- `User.Read` (basic profile resolution)

### Required environment variables

Communication channels and integrations:

- `EXCHANGE_TOKEN` or `EXCHANGE_TOKEN_SECRET_NAME` (Microsoft Graph token; optional Azure Key Vault secret name)
- `TEAMS_TOKEN` or `TEAMS_TOKEN_SECRET_NAME` (Teams Graph token; optional Azure Key Vault secret name)
- `SLACK_BOT_TOKEN` or `SLACK_BOT_TOKEN_SECRET_NAME` (Slack bot token; optional Azure Key Vault secret name)
- `COMMUNICATIONS_KEYVAULT_URL` (Azure Key Vault URL when using secret names)
- `GRAPH_BASE_URL` (optional, defaults to `https://graph.microsoft.com/v1.0`)

Email fallbacks:

- `AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING` (ACS Email connection string)
- `SENDGRID_API_KEY` and `SENDGRID_FROM_EMAIL` (SendGrid fallback)

AI + analytics:

- `AZURE_TEXT_ANALYTICS_ENDPOINT` and `AZURE_TEXT_ANALYTICS_KEY` (sentiment analysis)
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`
- `AZURE_ML_ENDPOINT` and `AZURE_ML_API_KEY` (engagement scoring)

Workflow automation + audit logging:

- `LOGIC_APPS_TRIGGER_URL` or `POWER_AUTOMATE_TRIGGER_URL` (workflow triggers)
- `SERVICE_BUS_CONNECTION_STRING` plus `SERVICE_BUS_TOPIC` or `SERVICE_BUS_QUEUE`

Data storage:

- `STAKEHOLDER_COMMS_DB_URL` (e.g., `postgresql+psycopg://user:pass@host/db`)

CRM sync (Salesforce connector):

- `SALESFORCE_INSTANCE_URL`, `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, `SALESFORCE_REFRESH_TOKEN`
- `SALESFORCE_TOKEN_URL` (from connector manifest)
- Optional: `SALESFORCE_CONTACT_ENDPOINT`, `SALESFORCE_CONTACT_QUERY`

### Local run + deploy

Local development:

```bash
python -m tools.agent_runner run-agent --name agent-21-stakeholder-comms --dry-run
```

Docker build and run:

```bash
docker build -t stakeholder-comms-agent agents/operations-management/agent-21-stakeholder-comms
docker run --env-file .env stakeholder-comms-agent
```

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
