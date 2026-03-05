# Workspace Setup Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Workspace Setup Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

The Workspace Setup agent manages the initialisation and configuration of project workspaces before any data is written to systems of record. It acts as a governed "setup wizard" phase that ensures connectors are enabled, authentication is complete, field mappings are set, and all required external artefacts and containers exist (Teams channels, SharePoint sites, Jira projects, Planview shells, etc.) before downstream delivery begins.

No write to a system of record is permitted until workspace setup is complete. This agent enforces that gate.

## Intended scope

### Responsibilities

#### B1: Project workspace initialisation
- Create the internal project workspace record in the platform's data store.
- Create the baseline artefact folder structure following organisational templates.
- Provision default canvas tabs and views: methodology map (lifecycle visualisation), dashboard (project health summary), registers (risk, issue, change, decision).

#### B2: Connector configuration gating
- Present required connectors by category: PPM tools (Planview, Clarity, Microsoft Project), PM tools (Jira, Azure DevOps, Monday.com), ERP systems (SAP, Oracle), Document management (SharePoint, Confluence), Collaboration (Teams, Slack), GRC (ServiceNow GRC, Archer).
- Validate connector status progression: `Not configured` → `Configured` → `Connected` → `Permissions validated`.
- Support connection testing: execute "Test connection" checks against each configured connector to verify credentials and endpoint reachability.
- Support dry-run mapping: execute "Dry-run mapping" checks to verify that field mappings between the platform and external systems produce valid results without writing data.
- Store per-project connector selections and configuration state: persist which connectors are active for each project and their current validation status.

#### B3: External workspace provisioning
- Create or link external assets as configured and permitted by organisational policy (Teams team/channels, SharePoint sites/libraries, Jira projects/boards, Planview project shells).
- Any provisioning or write action MUST route through the Approval Workflow agent for approval if organisational policy requires it.

#### B4: Methodology selection and bootstrap
- Allow the project to select its delivery methodology — predictive, hybrid, or adaptive — and load the corresponding lifecycle map.
- Apply organisation template defaults: load the organisation's default stages, gates, artefact requirements, and review criteria for the selected methodology.
- Mark "Setup complete" as a prerequisite for any publishing actions to systems of record and lifecycle progression beyond the initiation/setup phase.

### Inputs
- Project record from portfolio decision (project ID, metadata, selected methodology).
- Organisation connector configuration defaults.
- Project-specific connector overrides and preferences.
- Provisioning policy rules (which external assets to create, approval requirements).
- Methodology templates and lifecycle maps.

### Outputs
- Internal workspace record with folder structure and canvas configuration.
- Connector configuration state (per-project, per-connector validation status).
- Provisioned or linked external assets with IDs and URLs.
- Setup status checklist report (pass/fail status for each setup item with remediation guidance).
- Provisioned Assets registry (Teams team/channel ID and URL, SharePoint site/library URL, Jira project key and URL, Planview project ID and URL).
- Events published: `workspace.setup.started`, `workspace.setup.completed`, `workspace.setup.failed` (all include `tenant_id`, `project_id`, `correlation_id`, and `timestamp`).

### Decision responsibilities
- Which connectors are required vs. optional for a given project type.
- Whether external provisioning requires approval (based on organisational policy).
- Whether to create new external assets or link existing ones.
- When setup is complete and the project can proceed to delivery.

### Must / must-not behaviors
- **Must** enforce connector readiness, approval (where policy requires), and dry-run capability before external writes.
- **Must** persist workspace records, connector state, and provisioned assets registry.
- **Must** emit setup lifecycle events for downstream governance agents.
- **Must not** participate in demand classification, business case evaluation, or portfolio prioritisation.
- **Must not** enforce lifecycle transitions (the Lifecycle Governance agent uses setup completion status as a gate input).
- **Must not** create charter or scope content (the Project Definition and Scope agent owns those).

## Overlap & handoff boundaries

### Portfolio decision agents (Demand Intake, Business Case, Portfolio Strategy)
- **Overlap risk**: workspace setup follows portfolio decision.
- **Boundary**: After portfolio decision (project approved for execution), the Workspace Setup agent is invoked to prepare the project workspace. The Workspace Setup agent does not participate in demand classification, business case evaluation, or portfolio prioritisation.

### Approval Workflow
- **Overlap risk**: provisioning actions that require approval.
- **Boundary**: Provisioning actions that require approval are routed through the Approval Workflow agent. The Workspace Setup agent creates approval requests and waits for decisions before executing governed provisioning steps. The Workspace Setup agent owns the provisioning logic; the Approval Workflow agent owns the approval decision process.

### Project Lifecycle Governance
- **Overlap risk**: setup completion gates lifecycle progression.
- **Boundary**: The `workspace.setup.completed` event is consumed by the Lifecycle Governance agent to gate lifecycle progression. No project can advance beyond the initiation/setup phase until workspace setup is complete. The Workspace Setup agent does not enforce lifecycle transitions.

### Project Definition and Scope
- **Overlap risk**: workspace readiness precedes scope definition.
- **Boundary**: Once workspace setup is complete, the Project Definition and Scope agent can begin creating the project charter and scope baseline within the provisioned workspace. The Workspace Setup agent provides the workspace; the Project Definition and Scope agent owns the charter and scope content.

### Data Synchronisation
- **Overlap risk**: connector validation overlaps with sync operations.
- **Boundary**: The Workspace Setup agent uses the connector registry and connector runner (shared with the Data Synchronisation agent) to validate connectivity and execute dry-run mappings. The Workspace Setup agent validates connectivity at setup time; the Data Synchronisation agent manages ongoing sync operations.

## Functional gaps / inconsistencies & alignment needs

- Connector validation depends on external system availability; ensure graceful degradation and clear error reporting when endpoints are unreachable.
- Provisioning policy rules need to be documented and configurable per organisation/tenant.
- Methodology templates must stay in sync with the Lifecycle Governance agent's gate definitions.
- UI should surface setup status checklist with pass/fail indicators and remediation links.

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

### Dependency map entry

| Entry | Details |
| --- | --- |
| **Upstream dependencies** | Portfolio decision (project approved); connector registry; organisation configuration templates. |
| **Downstream dependencies** | Project Lifecycle Governance agent (setup complete gate); Project Definition and Scope agent (workspace ready); delivery agents (connectors validated). |
| **Peer dependencies** | Approval Workflow agent (governed provisioning approvals); Data Synchronisation agent (connector runner, mapping validation). |
| **Data contracts** | Workspace record schema, connector configuration schema, provisioned assets schema, setup status schema, and event payloads (`workspace.setup.*`). |
| **External systems** | Teams Graph API, SharePoint REST API, Jira REST API, Planview OData API, SAP APIs (as configured). |

### Lifecycle position

1. **Demand and Intake** → **Business Case** → **Portfolio decision** (project approved)
2. **Workspace Setup** ← this agent
3. **Project Lifecycle Governance** + **Project Definition and Scope** → downstream delivery agents

This sequence ensures that all external systems are configured and accessible before any delivery agent attempts to read from or write to them.

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

### Integration services used

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
