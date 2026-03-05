# Release Deployment Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Release Deployment Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Own release planning, readiness assessment, deployment orchestration, environment management, rollback, and post-deployment verification across environments (dev/test/stage/prod).
- Integrate with approvals, scheduling, environment reservation, configuration management, CI/CD, monitoring, analytics, and documentation publishing for release execution governance.

### Inputs
- `action`: action-driven payloads including `plan_release`, `assess_readiness`, `execute_deployment`, `rollback_deployment`, `manage_environment`, `check_drift`, `generate_release_notes`, `get_metrics`, `verify_deployment`.
- `release`: release payload with name, target environment, version, components.
- `release_id`, `deployment_plan_id`, `environment_id`: entity identifiers.
- `deployment_plan`, `environment`, `verification_params`, `filters`: action-specific payloads.
- Required inputs are enforced for key actions (e.g., `plan_release` requires name/target_environment, `execute_deployment` requires deployment_plan_id).

### Outputs
- Release IDs/schedules, readiness assessments with go/no-go recommendations.
- Deployment plans and statuses, rollback outcomes.
- Environment configurations, drift checks.
- Release notes, metrics, and verification results.

### Decision responsibilities
- **Go/No-Go**: computed in readiness assessment using approvals, change readiness, environment readiness, test/coverage gates, and blocker collection, yielding a recommendation and score.
- **Approval gating**: required for production (configurable), relies on the Approval Workflow agent when configured; blocks execution if not approved or not configured.
- **Rollback decisions**: auto-rollback triggered on anomaly thresholds or verification failures; manual rollback action supported with rollback scripts and orchestration steps.

### Must / must-not behaviors
- **Must** enforce readiness gates when enabled; check approval requirements for protected environments.
- **Must** log and persist release/deployment state; emit events for readiness and rollback lifecycle updates.
- **Must not** proceed to deployment when readiness gates recommend NO-GO or approvals are missing/unapproved.
- **Must not** skip rollback actions when auto-rollback triggers or verification fails if `auto_rollback_on_anomaly` is enabled.

## Overlap & handoff boundaries

### Quality Management
- **Overlap risk**: quality metrics, test results, defect density, and coverage gates are referenced by readiness checks (quality is a shared dependency).
- **Boundary**: The Release Deployment agent should consume quality signals from the Quality Management agent instead of duplicating test/defect management workflows. The Quality Management agent provides gate results (pass/fail + metrics + defects summary) to the Release Deployment agent for final release decisioning.

### Change Control
- **Overlap risk**: change approvals and configuration drift checks intersect with change management and CMDB ownership.
- **Boundary**: The Release Deployment agent should request change approval status and configuration drift/CMDB baselines from the Change Control agent rather than authoring change records itself. The Change Control agent provides approved change tickets/config baselines + risk/impact summaries.

## Functional gaps / inconsistencies & alignment needs

- **Prompt/template alignment**: readiness criteria are partially implicit (approval/test/coverage/quality/environment readiness) but not surfaced as a formal checklist template; require a release readiness template to standardize inputs and outputs for orchestration UI/workflow.
- **Connector alignment**: readiness checks expect approval and change signals, but connectors are not enforced; add explicit connector requirements for quality/change systems (e.g., CI pipelines, test management, CMDB) to avoid silent "pass" defaults.
- **UI alignment**: release calendar, deployment plans, and readiness assessments are stored but UI references are absent; requires UI surfaces for release calendar, deployment history, and gate status to prevent opaque decisions.

## Checkpoint: release readiness criteria

The release agent's current readiness gates are execution-ready as long as upstream signals are wired:
1. **Approvals complete** (release + change approvals).
2. **Quality gates pass** (test/coverage/defect thresholds).
3. **Environment readiness** (availability + config drift checks).
4. **Risk/compliance checks** (via risk/compliance agents when configured).
5. **Go/No-Go recommendation** is computed and enforced when `enforce_readiness_gates` is enabled.

## What's inside

- [src](/agents/operations-management/release-deployment-agent/src): Implementation source for this component.
- [tests](/agents/operations-management/release-deployment-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/operations-management/release-deployment-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name release-deployment-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/release-deployment-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
