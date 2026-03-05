# Compliance Governance Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Compliance Governance Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Maintain regulatory and compliance control catalogs (SOX, GDPR, ISO 27001, NIST, industry-specific).
- Map compliance controls to project activities, deliverables, and governance gates.
- Collect, validate, and store compliance evidence and attestations.
- Monitor ongoing compliance status and trigger alerts on non-compliance.
- Generate compliance reports, audit readiness assessments, and regulatory submissions.
- Provide compliance attestations as gate criteria evidence for the Lifecycle Governance agent.

### Inputs
- `action`: `map_controls`, `collect_evidence`, `assess_compliance`, `generate_report`, `get_control_status`, `update_control_mapping`, `submit_attestation`.
- `project_id` / `portfolio_id`: entity identifiers for compliance scope.
- `framework`: regulatory framework identifier (e.g., `SOX`, `GDPR`, `ISO27001`).
- `evidence` payload: attestation documents, sign-offs, audit artifacts.
- `context`: `tenant_id`, `correlation_id` (optional; used for audit/event metadata).

### Outputs
- Control mapping records linking regulatory requirements to project activities.
- Evidence collection status and validation results.
- Compliance assessment scores and gap analysis.
- Compliance reports and audit readiness summaries.
- Event emission: `compliance.assessment.completed`, `compliance.violation.detected`.

### Decision responsibilities
- Determine which regulatory frameworks apply to a given project based on classification.
- Assess compliance status based on evidence completeness and control effectiveness.
- Flag non-compliance and recommend remediation actions.
- Decide when compliance attestations are sufficient for governance gate evidence.

### Must / must-not behaviors
- **Must** validate evidence against control requirements before marking controls as satisfied.
- **Must** persist all compliance records with immutable audit trails.
- **Must** publish compliance events for downstream governance and analytics consumption.
- **Must** provide attestation evidence to the Lifecycle Governance agent when requested for gate evaluations.
- **Must not** approve or reject project lifecycle transitions (delegated to the Lifecycle Governance agent).
- **Must not** modify risk registers or mitigation plans (delegated to the Risk Management agent).
- **Must not** alter change control records or CMDB entries (delegated to the Change Control agent).

## Overlap & handoff boundaries

### Lifecycle Governance
- **Overlap risk**: compliance attestations are gate criteria for lifecycle transitions.
- **Boundary**: The Compliance Governance agent supplies regulatory/compliance attestations that become gate criteria evidence. The Lifecycle Governance agent owns lifecycle gating and phase transition decisions.

### Risk Management
- **Overlap risk**: compliance violations may create or escalate risks.
- **Boundary**: The Compliance Governance agent identifies compliance gaps and violations. The Risk Management agent owns risk register entries, scoring, and mitigation plans. The Compliance Governance agent may emit events that the Risk Management agent consumes to create risk entries.

## Functional gaps / inconsistencies & alignment needs

- **Compliance monitoring gap**: define an event contract or API call between the Compliance Governance agent and the Lifecycle Governance agent for compliance evidence exchange.
- **Framework configuration**: document how regulatory frameworks are configured and maintained per tenant/organisation.
- **Evidence ingestion**: define supported evidence formats and validation rules.
- **UI alignment**: compliance dashboards should surface control mapping status, evidence collection progress, and audit readiness scores.

## Checkpoint: compliance control mapping + dependency map entry

### Compliance control mapping criteria
- All applicable regulatory frameworks identified for the project.
- Controls mapped to project activities and deliverables.
- Evidence collection requirements defined per control.
- Compliance assessment baseline established.

### Dependency map entry
- **Upstream**: Project classification and regulatory requirements, audit evidence sources.
- **Core services**: document storage, audit trail, event bus.
- **Downstream**: Lifecycle Governance agent (compliance gate evidence), Risk Management agent (compliance violation signals), Analytics Insights agent (compliance metrics for dashboards).

## What's inside

- [src](/agents/delivery-management/compliance-governance-agent/src): Implementation source for this component.
- [tests](/agents/delivery-management/compliance-governance-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/delivery-management/compliance-governance-agent/Dockerfile): Container build recipe for local or CI use.
- [COMPLIANCE_CONTROL_CATALOG.md](/agents/delivery-management/compliance-governance-agent/COMPLIANCE_CONTROL_CATALOG.md): Scope validation, control catalog, and handoff boundaries for execution readiness.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name compliance-governance-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/compliance-governance-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
