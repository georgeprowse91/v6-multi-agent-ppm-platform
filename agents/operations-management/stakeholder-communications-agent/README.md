# Stakeholder Communications Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Stakeholder Communications Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Maintain the stakeholder register and engagement profiles.
- Classify stakeholders (influence/interest) and recommend engagement strategies.
- Build communication plans tied to portfolio/project updates.
- Generate, edit, schedule, and send outbound messages (email/Teams/Slack/SMS/push/portal).
- Collect feedback and sentiment, track engagement, and produce comms reports.
- Coordinate events/meetings and publish comms events to workflow/analytics systems.

### Inputs
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

### Decision responsibilities
- Determining stakeholder classifications and engagement strategies.
- Selecting delivery channels based on preferences, consent, and channel availability.
- Scheduling batches/digests and optimizing send times.
- Generating and personalizing message content.
- Triggering workflow automation and publishing comms events/metrics.

### Must / must-not behaviors
- **Must** enforce consent/opt-out rules before sending communications.
- **Must** store communication history and emit comms events for downstream analytics.
- **Must** respect delivery modes (immediate, scheduled, digest) and batching controls.
- **Must** provide traceable outputs for stakeholder updates and message actions.
- **Must not** send outbound communications requiring approval before the Approval Workflow agent approval is granted.
- **Must not** modify or overwrite authoritative knowledge documents owned by the Knowledge Management agent.
- **Must not** exfiltrate or log secrets; use configured secret providers only.

## Overlap & handoff boundaries

### Approval Workflow
- **Overlap risk**: outbound communications that require approval or escalation.
- **Boundary**: The Stakeholder Communications agent submits message drafts + metadata to the Approval Workflow agent for approval when policy or content flags require it. The Stakeholder Communications agent resumes delivery only after approval status is returned. The Approval Workflow agent owns approval decisions, audit trails, and approval notifications. The Stakeholder Communications agent owns message preparation, delivery execution, and delivery telemetry.

### Knowledge Management
- **Overlap risk**: content summaries or reports that could become knowledge artifacts.
- **Boundary**: The Stakeholder Communications agent can request approved knowledge snippets or finalized documents from the Knowledge Management agent to use in communications; the Stakeholder Communications agent can submit post-communication summaries for capture. The Knowledge Management agent manages canonical documents, versioning, and distribution repositories; the Stakeholder Communications agent only references or links those artifacts in outbound messages.

## Functional gaps / inconsistencies & alignment needs

- **Approval enforcement**: current implementation flags `review_required` but does not block send; align with the Approval Workflow agent by adding a required approval state gate.
- **CRM alignment**: README lists Salesforce-specific variables while implementation supports generic CRM endpoints; document precedence and mapping.
- **Connector alignment**: notification/calendar integrations are used in code but not documented in required env vars; add connector configuration or defaults.
- **Templates/UI alignment**: communication templates and digest batching lack UI/portal configuration detail; define where templates live and how they are reviewed.
- **Telemetry alignment**: define how delivery events map to analytics (the Analytics Insights agent) and knowledge capture (the Knowledge Management agent).

## Checkpoint: communications trigger matrix

| Trigger | Inputs | Action | Approval required | Output/records | Handoff |
| --- | --- | --- | --- | --- | --- |
| Stakeholder added | `stakeholder` payload | Register stakeholder + classify | No (unless policy) | Stakeholder profile, classification | Optionally send profile summary to the Knowledge Management agent |
| Project status update | `report`/summary source | Generate update message | Yes if external audience | Draft message, summary, delivery plan | Send draft to the Approval Workflow agent for approval |
| Risk/issue escalation | Risk payload + audience | Send escalation comms | Yes | Delivery results + history | Coordinate approvals with the Approval Workflow agent |
| Change request | Change details + audience | Compose change notice | Yes | Message + delivery telemetry | the Approval Workflow agent approval, the Knowledge Management agent update |
| Release milestone | Release notes | Broadcast release update | Yes if external | Message + schedule | the Approval Workflow agent approval; the Knowledge Management agent docs link |
| Stakeholder feedback received | Feedback payload | Analyze sentiment + update engagement | No | Sentiment score, engagement update | Feed analytics/knowledge |
| Event/meeting scheduled | Event details | Send invites/notifications | No (internal) | Calendar event, notifications | Calendar integration |
| Engagement drop | Engagement metrics | Trigger re-engagement plan | Maybe (policy) | New plan + draft message | the Approval Workflow agent approval if required |

## What's inside

- [src](/agents/operations-management/stakeholder-communications-agent/src): Implementation source for this component.
- [tests](/agents/operations-management/stakeholder-communications-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/operations-management/stakeholder-communications-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name stakeholder-communications-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/stakeholder-communications-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

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

Docker build and run:

```bash
docker build -t stakeholder-comms-agent agents/operations-management/stakeholder-communications-agent
docker run --env-file .env stakeholder-comms-agent
```

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
