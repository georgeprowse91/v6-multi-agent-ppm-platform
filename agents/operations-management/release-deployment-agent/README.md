# Release Deployment Specification

## Purpose

Define the responsibilities, workflows, and integration points for Release Deployment. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

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

## Release Deployment validation notes (scope, I/O, decisions, handoffs)

### Intended scope
- Owns release planning, readiness assessment, deployment orchestration, environment management, rollback, and post-deployment verification across environments (dev/test/stage/prod).【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L20-L133】
- Integrates with approvals, scheduling, environment reservation, configuration management, CI/CD, monitoring, analytics, and documentation publishing for release execution governance.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L86-L166】

### Inputs / outputs
- **Inputs:** action-driven payloads including `release`, `release_id`, `deployment_plan`, `deployment_plan_id`, `environment`, `environment_id`, `verification_params`, and `filters`. Required inputs are enforced for key actions (e.g., `plan_release` requires name/target_environment, `execute_deployment` requires deployment_plan_id).【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L152-L205】
- **Outputs:** action-specific responses including release IDs/schedules, readiness assessments with go/no-go, deployment plans and statuses, rollback outcomes, environment configurations, drift checks, release notes, metrics, and verification results.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L206-L340】

### Decision responsibilities
- **Go/No-Go:** computed in readiness assessment using approvals, change readiness, environment readiness, test/coverage gates, and blocker collection, yielding a recommendation and score.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L464-L544】【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L2373-L2564】
- **Approval gating:** required for production (configurable), relies on approval workflow agent when configured; blocks execution if not approved or not configured.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L56-L132】【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L648-L705】
- **Rollback decisions:** auto-rollback triggered on anomaly thresholds or verification failures; manual rollback action supported with rollback scripts and orchestration steps.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L758-L896】【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L1554-L1574】

### Must / must-not behaviors
- **Must:** enforce readiness gates when enabled; check approval requirements for protected environments; log and persist release/deployment state; emit events for readiness and rollback lifecycle updates.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L80-L705】【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L842-L896】
- **Must not:** proceed to deployment when readiness gates recommend NO-GO or approvals are missing/unapproved; must not skip rollback actions when auto-rollback triggers or verification fails if `auto_rollback_on_anomaly` is enabled.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L648-L705】【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L792-L896】

### Overlap / leakage with the Quality Management agent (Quality) & the Change Control agent (Change/Configuration)
- **The Quality Management agent overlap:** quality metrics, test results, defect density, and coverage gates are referenced by readiness checks (quality is a shared dependency). Release agent should consume quality signals from the Quality Management agent instead of duplicating test/defect management workflows.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L486-L507】【F:agents/delivery-management/quality-management-agent/src/quality_management_agent.py†L20-L174】
- **The Change Control agent overlap:** change approvals and configuration drift checks intersect with change management and CMDB ownership. Release agent should request change approval status and configuration drift/CMDB baselines from the Change Control agent rather than authoring change records itself.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L1350-L1536】【F:agents/operations-management/change-control-agent/src/change_configuration_agent.py†L20-L174】

### Handoff boundaries
- **From the Change Control agent → the Release Deployment agent:** approved change tickets/config baselines + risk/impact summaries. the Release Deployment agent consumes approvals to satisfy readiness gates and schedules deployments accordingly.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L477-L507】【F:agents/operations-management/change-control-agent/src/change_configuration_agent.py†L20-L174】
- **From the Quality Management agent → the Release Deployment agent:** verified test execution results, coverage snapshots, and defect status to satisfy readiness criteria and post-deployment verification inputs.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L486-L507】【F:agents/delivery-management/quality-management-agent/src/quality_management_agent.py†L20-L174】
- **From the Release Deployment agent → the Change Control agent:** deployment outcomes, rollback events, and configuration drift discoveries to update change records/CMDB for closure and audit trail.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L842-L896】

### Functional gaps / inconsistencies & alignment needs
- **Prompt/template alignment:** readiness criteria are partially implicit (approval/test/coverage/quality/environment readiness) but not surfaced as a formal checklist template; require a release readiness template to standardize inputs and outputs for orchestration UI/workflow.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L486-L507】
- **Connector alignment:** readiness checks expect approval and change signals, but connectors are not enforced; add explicit connector requirements for quality/change systems (e.g., CI pipelines, test management, CMDB) to avoid silent “pass” defaults.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L1334-L1536】
- **UI alignment:** release calendar, deployment plans, and readiness assessments are stored but UI references are absent; requires UI surfaces for release calendar, deployment history, and gate status to prevent opaque decisions.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L702-L888】

### Release readiness criteria (ready for execution)
The release agent’s current readiness gates are execution-ready as long as upstream signals are wired:
1. **Approvals complete** (release + change approvals).【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L477-L507】
2. **Quality gates pass** (test/coverage/defect thresholds).【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L486-L507】
3. **Environment readiness** (availability + config drift checks).【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L368-L417】【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L1121-L1215】
4. **Risk/compliance checks** (via risk/compliance agents when configured).【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L96-L106】【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L2373-L2564】
5. **Go/No-Go recommendation** is computed and enforced when `enforce_readiness_gates` is enabled.【F:agents/operations-management/release-deployment-agent/src/release_deployment_agent.py†L80-L705】
