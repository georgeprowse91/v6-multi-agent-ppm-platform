# Compliance Control Catalog & Scope Validation (Agent 16)

## Intended scope

Agent 16 owns compliance and regulatory management across projects/programs/portfolios, including:

- Managing regulatory frameworks, controls, evidence, and audit packages.
- Monitoring regulatory updates and notifying stakeholders.
- Producing compliance dashboards and reports.
- Verifying release compliance signals from delivery events.

The agent implements a request-driven interface with explicit actions for regulation intake, control definitions, control mapping to projects, compliance assessment/testing, policy management, audit preparation/execution, evidence handling, regulatory change monitoring, and reporting.

## Inputs & outputs

### Inputs

The agent expects an `action` in the request payload and supports the following actions:

- `add_regulation`
- `define_control`
- `map_controls_to_project`
- `assess_compliance`
- `test_control`
- `manage_policy`
- `prepare_audit`
- `conduct_audit`
- `upload_evidence`
- `monitor_regulatory_changes`
- `get_compliance_dashboard`
- `generate_compliance_report`
- `verify_release_compliance`
- `list_evidence`
- `get_evidence`
- `list_reports`
- `get_report`

Each action accepts structured payloads (e.g., `regulation`, `control`, `mapping`, `assessment`, `test`, `policy`, `audit`, `evidence`, `project_id`, `filters`) and optional `context` fields such as `tenant_id` and `correlation_id`.

### Outputs

The agent returns action-specific outputs. Key outputs include:

- Regulation identifiers and applicability results from `add_regulation`.
- Control identifiers, requirements, and checklists from `define_control`/`map_controls_to_project`.
- Compliance assessments with gap analysis and recommendations from `assess_compliance`.
- Audit packages and findings from `prepare_audit`/`conduct_audit`.
- Evidence identifiers and snapshots from `upload_evidence`/`list_evidence`/`get_evidence`.
- Dashboards and reports from `get_compliance_dashboard`/`generate_compliance_report`.
- Release compliance verdicts from `verify_release_compliance`.

## Decision responsibilities

### Agent 16 is responsible for:

- Determining regulatory applicability for a project based on industry, geography, and data sensitivity.
- Defining controls and assigning test frequencies to ensure regulatory obligations are satisfied.
- Assessing compliance evidence against control requirements and scoring compliance gaps.
- Preparing audit documentation packages and summarizing audit findings.
- Monitoring regulatory changes and identifying impacted controls.
- Publishing notifications and compliance events for downstream systems.

### Agent 16 is **not** responsible for:

- Project phase gating, health scoring, or lifecycle state transitions (owned by Agent 09).
- Vendor onboarding, procurement approvals, or vendor compliance enforcement (owned by Agent 13).
- Approving releases or operational readiness; it only supplies compliance verification inputs.

## Must / must-not behaviors

### Must

- Must reject requests without an `action` or with unsupported actions.
- Must require control definitions to include `description`, `regulation`, and `owner` before creating a control.
- Must store compliance schemas, evidence snapshots, and reports in the configured persistence layer.
- Must evaluate evidence against control requirement checks (implemented/evidence/tested/audit logs/etc.) using the compliance rule engine.

### Must not

- Must not proceed with an undefined action.
- Must not define a control without the required fields.
- Must not conflate lifecycle governance or vendor procurement decisions into compliance responses.

## Compliance control catalog

The catalog below aligns with the built-in control schemas and compliance rule evaluation used by the agent. It can be used as the executable baseline for compliance checks until the GRC integration supplies authoritative control libraries.

### Core schema entities

| Schema | Purpose | Key fields |
| --- | --- | --- |
| `regulatory_frameworks` | Store regulatory framework metadata | `framework_id`, `name`, `description`, `jurisdiction`, `industry`, `data_sensitivity`, `effective_date`, `applicability_rules` |
| `control_requirements` | Define control requirements and ownership | `control_id`, `regulation_id`, `description`, `owner`, `control_type`, `requirements`, `evidence_requirements`, `test_frequency` |
| `control_mappings` | Map controls to projects | `mapping_id`, `project_id`, `industry`, `geography`, `data_sensitivity`, `control_ids`, `created_at` |
| `compliance_evidence` | Track evidence artifacts | `evidence_id`, `control_id`, `project_id`, `source_agent`, `metadata`, `created_at` |
| `compliance_reports` | Record generated reports | `report_id`, `report_type`, `framework`, `generated_at`, `report_url` |

### Requirement checks evaluated by the rules engine

The rule engine evaluates compliance evidence against a set of requirement checks. These checks should be used as the baseline control test catalog:

- `implemented`: evidence indicates the control is implemented.
- `evidence`: evidence artifact is uploaded.
- `tested`: evidence shows recent testing.
- `audit_logs`: audit logs exist for the control.
- `risk_mitigation`: risk mitigations are documented.
- `quality_tests`: quality testing evidence exists.
- `deployment_checks`: deployment verification evidence exists.
- `data_privacy`: privacy impact assessment completed.
- `security_scans`: security scan evidence exists.

## Overlap analysis & handoff boundaries

### Agent 09: Lifecycle Governance

**Overlap:**
- Both agents touch governance and release readiness signals.

**Boundary:**
- Agent 09 owns lifecycle stage transitions, gate enforcement, health scoring, and governance dashboards.
- Agent 16 supplies compliance inputs (controls, assessments, evidence, and release compliance checks) that can be consumed by Agent 09 for governance decisions.

**Handoff:**
- Agent 09 should request compliance checks (`verify_release_compliance`, `assess_compliance`) when preparing a gate evaluation.

### Agent 13: Vendor Procurement

**Overlap:**
- Both agents deal with compliance checks and audit evidence.

**Boundary:**
- Agent 13 owns vendor risk/compliance screening, sanctions/watchlist checks, and procurement lifecycle decisions.
- Agent 16 should only consume vendor compliance artifacts as evidence inputs when they are required for regulatory control testing or audits.

**Handoff:**
- Agent 13 produces vendor compliance status, risk scores, and sanctions findings; Agent 16 ingests them as evidence artifacts for regulatory controls.

## Functional gaps & alignment requirements

### Functional gaps / inconsistencies

- Compliance controls are stored in memory and a generic database service, but there is no explicit linkage to the shared metrics catalog used by governance health reporting.
- Release compliance checks exist, but there is no explicit mapping to lifecycle gate criteria; this should be coordinated with Agent 09.
- Regulatory change monitoring runs when configured, but no enforcement workflow is defined for required remediation tasks.

### Alignment needs (prompt/tool/template/connector/UI)

- **Prompt/tooling:** ensure orchestration prompts direct compliance assessments to Agent 16 and lifecycle gate decisions to Agent 09.
- **Templates:** align compliance report templates with governance health report templates (shared terminology for risks and gaps).
- **Connectors:** integrate GRC systems (ServiceNow GRC, RSA Archer) as authoritative sources for regulatory frameworks and controls.
- **UI:** surface compliance dashboards and audit packages alongside project governance dashboards for a single source of truth.

## Checkpoint: Compliance control catalog ready for execution

The catalog above is aligned to the agent’s current schemas and rule checks, and can be executed immediately using the existing `assess_compliance`, `test_control`, `upload_evidence`, and reporting actions.
