# Workspace Setup Specification

## Purpose

The Workspace Setup agent manages the initialisation and configuration of project workspaces before any data is written to systems of record. It acts as a governed "setup wizard" phase that ensures connectors are enabled, authentication is complete, field mappings are set, and all required external artefacts and containers exist (Teams channels, SharePoint sites, Jira projects, Planview shells, etc.) before downstream delivery begins.

No write to a system of record is permitted until workspace setup is complete. This agent enforces that gate.

## What's inside

- [src](/agents/core-orchestration/workspace-setup-agent/src): Implementation source for this component.
- [tests](/agents/core-orchestration/workspace-setup-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/core-orchestration/workspace-setup-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution. This agent is invoked after a portfolio decision has been made and before project lifecycle governance and delivery agents begin work.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name workspace-setup-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/core-orchestration/workspace-setup-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Intended scope and responsibilities

**The Workspace Setup agent owns the project workspace initialisation lifecycle.** It is responsible for:

### B1: Project workspace initialisation

- Create the internal project workspace record in the platform's data store.
- Create the baseline artefact folder structure following organisational templates.
- Provision default canvas tabs and views:
  - Methodology map (lifecycle visualisation)
  - Dashboard (project health summary)
  - Registers (risk, issue, change, decision)

### B2: Connector configuration gating

Manage project-scoped connector configuration with organisation defaults and project-level overrides:

- **Present required connectors by category:**
  - PPM tools (Planview, Clarity, Microsoft Project)
  - PM tools (Jira, Azure DevOps, Monday.com)
  - ERP systems (SAP, Oracle)
  - Document management (SharePoint, Confluence)
  - Collaboration (Teams, Slack)
  - GRC (ServiceNow GRC, Archer)

- **Validate connector status progression:**
  - `Not configured` → `Configured` → `Connected` → `Permissions validated`

- **Support connection testing:** Execute "Test connection" checks against each configured connector to verify credentials and endpoint reachability.
- **Support dry-run mapping:** Execute "Dry-run mapping" checks to verify that field mappings between the platform and external systems produce valid results without writing data.
- **Store per-project connector selections and configuration state:** Persist which connectors are active for each project and their current validation status.

### B3: External workspace provisioning

Create or link external assets as configured and permitted by organisational policy. All provisioning actions are governed:

- **Teams:** Create a Teams team and/or channel(s) with standard channel structure, or link an existing team/channel.
- **SharePoint:** Create a SharePoint site, document library, and folder structure with appropriate permissions, or link an existing site/library.
- **Jira:** Create a Jira project and board with templates applied, or link an existing project/board. Configure field mappings.
- **Planview:** Create a Planview project shell with field mappings configured, or link an existing project.

**Governance requirement:** Any provisioning or write action MUST route through the Approval Workflow agent for approval if organisational policy requires it. The agent checks the applicable provisioning policy before executing any external write and, if approval is required, creates an approval request and waits for the decision before proceeding.

### B4: Methodology selection and bootstrap

- **Select methodology:** Allow the project to select its delivery methodology — predictive, hybrid, or adaptive — and load the corresponding lifecycle map.
- **Apply organisation template defaults:** Load the organisation's default stages, gates, artefact requirements, and review criteria for the selected methodology.
- **Setup complete gate:** Mark "Setup complete" as a prerequisite for:
  - Any publishing actions to systems of record.
  - Lifecycle progression beyond the initiation/setup phase.

### B5: Outputs and events

**Setup Status checklist report:**
- Pass/fail status for each setup item (workspace created, connectors validated, assets provisioned, methodology selected).
- Links to any failed items with remediation guidance.

**Provisioned Assets registry:**
- Registry of all created or linked external assets with their IDs and URLs:
  - Teams team/channel ID and URL
  - SharePoint site/library URL
  - Jira project key and URL
  - Planview project ID and URL

**Events published:**
- `workspace.setup.started` — Setup process initiated for a project.
- `workspace.setup.completed` — All setup items passed; workspace is ready for delivery.
- `workspace.setup.failed` — One or more setup items failed; workspace is not ready.

All events include `tenant_id`, `project_id`, `correlation_id`, and `timestamp`.

## Inputs, outputs, and decision responsibilities

**Inputs (primary):**

- Project record from portfolio decision (project ID, metadata, selected methodology).
- Organisation connector configuration defaults.
- Project-specific connector overrides and preferences.
- Provisioning policy rules (which external assets to create, approval requirements).
- Methodology templates and lifecycle maps.

**Outputs (primary):**

- Internal workspace record with folder structure and canvas configuration.
- Connector configuration state (per-project, per-connector validation status).
- Provisioned or linked external assets with IDs and URLs.
- Setup status checklist report.
- Provisioned Assets registry.
- Setup lifecycle events (`workspace.setup.started`, `workspace.setup.completed`, `workspace.setup.failed`).

**Decision responsibilities:**

- Which connectors are required vs. optional for a given project type.
- Whether external provisioning requires approval (based on organisational policy).
- Whether to create new external assets or link existing ones.
- When setup is complete and the project can proceed to delivery.

## Overlap boundaries and handoffs

**Upstream: Portfolio decision agents (Demand and Intake, Business Case, Portfolio Strategy):**

- **Upstream handoff:** After portfolio decision (project approved for execution), the Workspace Setup agent is invoked to prepare the project workspace.
- **Boundary:** the Workspace Setup agent does not participate in demand classification, business case evaluation, or portfolio prioritisation.

**The Approval Workflow agent (Approval Workflow):**

- **Handoff:** Provisioning actions that require approval are routed through the Approval Workflow agent. The Workspace Setup agent creates approval requests and waits for decisions before executing governed provisioning steps.
- **Boundary:** the Workspace Setup agent owns the provisioning logic; the Approval Workflow agent owns the approval decision process.

**Downstream: Project Lifecycle Governance agent:**

- **Downstream handoff:** The `workspace.setup.completed` event is consumed by the Lifecycle Governance agent to gate lifecycle progression. No project can advance beyond the initiation/setup phase until workspace setup is complete.
- **Boundary:** the Workspace Setup agent does not enforce lifecycle transitions; the Lifecycle Governance agent uses setup completion status as a gate input.

**Downstream: Project Definition and Scope agent:**

- **Downstream handoff:** Once workspace setup is complete, the Project Definition and Scope agent can begin creating the project charter and scope baseline within the provisioned workspace.
- **Boundary:** the Workspace Setup agent provides the workspace; the Project Definition and Scope agent owns the charter and scope content.

**The Data Synchronisation agent (Data Synchronisation and Quality):**

- **Handoff:** The Workspace Setup agent uses the connector registry and connector runner (shared with the Data Synchronisation agent) to validate connectivity and execute dry-run mappings.
- **Boundary:** the Workspace Setup agent validates connectivity at setup time; the Data Synchronisation agent manages ongoing sync operations.

## Lifecycle position

The Workspace Setup agent operates at a specific point in the platform lifecycle:

1. **Demand and Intake** → **Business Case** → **Portfolio decision** (project approved)
2. **Workspace Setup** ← this agent
3. **Project Lifecycle Governance** + **Project Definition and Scope** → downstream delivery agents

This sequence ensures that all external systems are configured and accessible before any delivery agent attempts to read from or write to them.

## Checkpoint: setup status items

| Item | Category | Validation | Required |
| --- | --- | --- | --- |
| **Workspace created** | B1 | Internal record exists with folder structure | Yes |
| **Canvas tabs provisioned** | B1 | Methodology map, dashboard, and registers tabs created | Yes |
| **Required connectors configured** | B2 | All required connectors at `Permissions validated` status | Yes |
| **Optional connectors configured** | B2 | Optional connectors at `Configured` or above | No |
| **External assets provisioned** | B3 | All policy-required external assets created or linked | Per policy |
| **Methodology selected** | B4 | Lifecycle map loaded and template defaults applied | Yes |
| **Setup complete gate** | B4 | All required items passed | Yes |

## Checkpoint: dependency map entry

| Entry | Details |
| --- | --- |
| **Upstream dependencies** | Portfolio decision (project approved); connector registry; organisation configuration templates. |
| **Downstream dependencies** | Project Lifecycle Governance agent (setup complete gate); Project Definition and Scope agent (workspace ready); delivery agents (connectors validated). |
| **Peer dependencies** | Approval Workflow agent (governed provisioning approvals); Data Synchronisation agent (connector runner, mapping validation). |
| **Data contracts** | Workspace record schema, connector configuration schema, provisioned assets schema, setup status schema, and event payloads (`workspace.setup.*`). |
| **External systems** | Teams Graph API, SharePoint REST API, Jira REST API, Planview OData API, SAP APIs (as configured). |

## Integration services used

The workspace-setup-agent consumes the following shared integration services from `agents/common/connector_integration.py`:

| Service | Usage |
| --- | --- |
| **DocumentManagementService** | Create SharePoint document libraries, folders, and initial artefact templates for the project workspace. |
| **ProjectManagementService** | Provision or link Jira projects/boards and Planview project shells. |
| **NotificationService** | Send workspace setup status notifications (email, Teams, Slack). |
| **DatabaseStorageService** | Persist workspace record, connector configuration state, provisioned assets registry, and setup status. |
| **CalendarIntegrationService** (optional) | Create shared project calendar entries for methodology gates/milestones. |

All write operations executed by this agent go through the `ConnectorWriteGate` to enforce connector readiness, approval (where policy requires), dry-run capability, and audit logging.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
- Connector validation fails: check that connector credentials are configured in the secrets store and that target endpoints are reachable.
- External provisioning fails with permission errors: verify that the platform's service principal has the required permissions in the target system (e.g., Teams admin consent, SharePoint site collection admin, Jira project admin).
