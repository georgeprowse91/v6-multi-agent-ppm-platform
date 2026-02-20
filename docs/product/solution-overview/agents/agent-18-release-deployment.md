> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 18 — Release and Deployment

**Category:** Operations Management
**Role:** Release Coordinator and Deployment Orchestrator

---

## What This Agent Is

The Release and Deployment agent coordinates the controlled movement of project outputs — software releases, infrastructure changes, process updates, or any other deliverable — from the delivery environment into production. It manages release planning, readiness assessment, deployment orchestration, and rollback procedures, ensuring that releases are planned, approved, monitored, and recorded.

For technology delivery programmes in particular, the release process is where months of delivery work either succeeds or fails in its final step. This agent ensures that step is taken carefully, with the right information, at the right time, with a clear path back if things go wrong.

---

## What It Does

**It plans releases.** The agent manages a release calendar, coordinating multiple planned releases across projects and environments. It considers scheduling constraints — maintenance windows, blackout periods, dependencies on other releases — and recommends optimal deployment windows that minimise risk and disruption. Calendar integration ensures that release windows appear alongside other commitments.

**It assesses release readiness.** Before a release can proceed, the agent performs a structured readiness assessment. It checks that all quality gate criteria have been met (from Agent 14), that all relevant change requests have been approved and incorporated (from Agent 17), that compliance clearance has been obtained (from Agent 16), that the target environment is available and correctly provisioned, and that the deployment plan has been reviewed and approved. Only when all readiness criteria are satisfied — a go/no-go decision — does the agent authorise the deployment to proceed.

**It orchestrates deployments.** Once a deployment is approved to proceed, the agent manages its execution through a structured deployment plan. The plan defines the sequence of deployment steps, the verification checks at each step, the parties responsible for each action, and the conditions that would trigger a rollback. The agent monitors execution against the plan in real time, recording the outcome of each step.

**It manages environment provisioning.** The agent tracks the configuration and availability of each deployment environment — development, test, staging, and production — ensuring that environments are correctly provisioned before a deployment is attempted and that environment configuration drift (where an environment has diverged from its expected configuration) is detected and addressed.

**It performs configuration drift checking.** Environments that have drifted from their approved configuration are a common source of deployment failures. The agent periodically checks each environment against its baseline configuration and flags any drift before a deployment is attempted, giving the team the opportunity to remediate the discrepancy rather than discovering it during deployment.

**It manages rollback procedures.** Every deployment plan includes a defined rollback procedure that specifies how to reverse the deployment if it fails or causes unacceptable issues. The agent manages rollback execution — triggering the rollback steps, monitoring their progress, and confirming when the environment has been successfully restored to its pre-deployment state.

**It generates release notes.** After a successful deployment, the agent produces release notes that summarise what was included in the release, what issues were resolved, what new capabilities were delivered, and any known limitations. Release notes are stored in the document canvas and can be distributed to stakeholders through the communications agent.

**It tracks deployment metrics.** The agent monitors deployment success rates, mean time to recovery, lead time from approval to deployment, and change failure rates. These metrics feed into the continuous improvement process and contribute to the organisation's DevOps maturity assessment.

---

## How It Works

The agent integrates with version control systems (GitHub, GitLab, Azure Repos) to access release artefacts and change sets, and with CI/CD pipeline tools (Azure DevOps, Jenkins) to trigger and monitor deployments. Environment management leverages Azure infrastructure tools. The readiness assessment is a structured gate that aggregates signals from multiple other agents before producing a go/no-go recommendation.

---

## What It Uses

- Quality gate status from Agent 14 — Quality Management
- Change approval records from Agent 17 — Change and Configuration Management
- Compliance clearance from Agent 16 — Compliance and Regulatory
- Repository integrations: GitHub, GitLab, Azure Repos
- CI/CD pipeline integrations: Azure DevOps
- Environment configuration and drift checking
- Release calendar with maintenance window and blackout period rules
- Agent 03 — Approval Workflow for deployment authorisation
- Agent 25 — System Health and Monitoring for post-deployment health checks

---

## What It Produces

- **Release plan**: a scheduled, prioritised list of upcoming releases with readiness status
- **Release readiness assessment**: a go/no-go evaluation summarising the status of all readiness criteria
- **Deployment plan**: a step-by-step execution plan with verification checks and rollback procedures
- **Deployment record**: a complete log of each deployment with step-by-step outcomes and timestamps
- **Rollback record**: a log of rollback executions with cause and resolution
- **Environment configuration record**: current state of each environment with drift indicators
- **Release notes**: a summary of each deployment's contents for stakeholder communication
- **Deployment metrics**: success rate, lead time, change failure rate, and mean time to recovery

---

## How It Appears in the Platform

Release planning is accessible from the Release Management stage in the **Methodology Map** and from the **Timeline Canvas**, where upcoming releases are shown as dated milestones. The release readiness dashboard — showing the status of each readiness criterion — is available in the **Dashboard Canvas**.

Deployment approval requests appear in the **Approvals** page. The deployment log and release notes are stored in the **Document Canvas**. The assistant panel can answer deployment questions: "Are we ready to release?" "What was included in last week's deployment?" "Has the production environment drifted from its baseline?"

---

## The Value It Adds

Deployment failures and post-release incidents are expensive — in remediation cost, in business disruption, and in the erosion of confidence in the delivery team. The Release and Deployment agent reduces the risk of deployment failures by enforcing a structured readiness gate, ensuring that releases only proceed when all the conditions for success are in place.

The rollback capability provides a safety net that gives teams the confidence to deploy more frequently — knowing that if something goes wrong, the path back is well-defined and tested.

---

## How It Connects to Other Agents

The Release and Deployment agent is a consumer of quality, compliance, and change data from **Agents 14, 16, and 17**. Deployment success is monitored by **Agent 25 — System Health and Monitoring** post-deployment. Deployment events are recorded in the change log maintained by **Agent 17**. Release metrics feed into **Agent 20 — Continuous Improvement** for DevOps maturity analysis, and into **Agent 22 — Analytics and Insights** for portfolio-level delivery reporting.
