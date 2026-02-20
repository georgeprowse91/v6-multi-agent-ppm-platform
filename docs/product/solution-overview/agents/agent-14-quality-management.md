> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 14 — Quality Management

**Category:** Delivery Management
**Role:** Quality Planner and Test Coordinator

---

## What This Agent Is

The Quality Management agent embeds quality assurance into the project delivery process rather than treating it as an end-of-cycle activity. It plans how quality will be measured and assured, manages the test process, tracks defects, enforces quality gate criteria, and provides the quality data that feeds into project health scoring and stage-gate assessments.

Its presence means that quality does not depend on a single person remembering to run tests or complete a review. It is a systematic, tracked, continuously monitored dimension of every project on the platform.

---

## What It Does

**It creates quality plans.** At the start of a project, the agent produces a quality management plan that defines the quality objectives, the standards that will be applied, the metrics that will be tracked, the review activities that will be conducted, and the gate criteria that must be satisfied before each stage transition. The plan is tailored to the project type and methodology — a quality plan for a software delivery project looks different from one for a capital infrastructure project.

**It manages test cases and test suites.** For technology delivery projects, the agent creates and organises test cases linked directly to the project's requirements register. Each test case specifies the scenario being tested, the expected outcome, the preconditions, and the acceptance criteria. Test cases are grouped into test suites that can be executed together. Test case generation uses the project's requirements as inputs, ensuring comprehensive coverage without requiring the test team to start from scratch.

**It tracks test execution and results.** As tests are run — whether manually or through automated test frameworks — the agent records the results: pass, fail, or blocked. It calculates pass rates, coverage percentages, and defect densities, and tracks these metrics against the quality gate thresholds defined in the quality plan.

**It manages the defect lifecycle.** When a test fails and a defect is identified, the agent creates a defect record with the relevant context: severity, priority, which requirement or test case it relates to, and the environment in which it was found. It tracks defects through their lifecycle — identified, assigned, in progress, resolved, verified — and applies configurable workflows to ensure that defects are not closed without proper verification. It integrates with Azure DevOps and Jira for teams that manage defects in those tools.

**It schedules and tracks reviews and audits.** Quality assurance involves more than testing. The agent schedules formal reviews — design reviews, code reviews, documentation reviews, security audits — tracks whether they have taken place, and records their outcomes. These review records contribute to the evidence base for stage-gate assessments.

**It enforces quality gate criteria.** Before a project can advance past a stage gate, the quality data must meet the defined thresholds: test pass rate above a configured minimum (commonly 95%), defect density below a threshold (commonly 0.05 defects per function point), code coverage above a minimum (commonly 80%), and all critical and high-severity defects resolved. The agent evaluates these criteria and provides a clear pass/fail assessment to the Lifecycle and Governance agent.

**It performs defect trend analysis.** The agent analyses defect patterns over time — identifying which components or requirements are generating the most defects, whether defect rates are improving or worsening as delivery progresses, and whether specific defect categories are recurring — and produces recommendations for targeted quality improvement.

**It integrates with test automation.** For organisations using Playwright or other automated testing frameworks, the agent can ingest automated test results and incorporate them into the quality picture alongside manually executed tests.

---

## How It Works

The agent creates its quality plan from the project's requirements register (from Agent 08) and methodology configuration. Test case generation uses the requirements as inputs, applying the platform's LLM to produce test scenarios from requirement descriptions. Defect prediction uses an Azure ML model to identify areas of the project most likely to generate defects based on historical patterns — allowing the test effort to be directed where it is most needed.

---

## What It Uses

- Requirements register from Agent 08 — Project Definition and Scope
- Methodology configuration for quality gate thresholds
- Azure DevOps and Jira integrations for bidirectional defect synchronisation
- Playwright automation integration for automated test result ingestion
- Azure ML model for defect prediction and test prioritisation
- TestRail integration for test management
- Code coverage metrics from connected code repositories
- Agent 09 — Project Lifecycle and Governance as the consumer of quality gate assessments
- Agent 03 — Approval Workflow for formal review and audit approvals

---

## What It Produces

- **Quality management plan**: objectives, standards, metrics, review schedule, and gate criteria
- **Test cases and test suites**: structured test scenarios linked to requirements
- **Test execution results**: pass/fail outcomes with coverage and pass rate metrics
- **Defect register**: tracked defect records with severity, priority, status, and lifecycle history
- **Quality gate assessment**: pass/fail evaluation of quality criteria for each stage gate
- **Defect trend analysis**: patterns and recommendations for quality improvement
- **Review and audit records**: evidence of completed quality activities
- **Quality dashboard**: real-time view of test coverage, pass rates, defect density, and quality gate status

---

## How It Appears in the Platform

Quality data is surfaced in the project workspace in two primary ways. The quality gate status is visible in the **Methodology Map** — the relevant stage shows a quality gate indicator that reflects whether the quality criteria have been met. The detailed quality dashboard — test pass rates, defect density, open defect count by severity — is available in the **Dashboard Canvas**.

Defect records and test cases are managed through the **Spreadsheet Canvas**, where they can be filtered, sorted, and updated. Review schedules appear in the project timeline in the **Timeline Canvas**.

The assistant panel supports quality queries: "How many critical defects are currently open?" "What is our test pass rate?" "Are we on track to pass the quality gate?" — returning current data in conversational format.

---

## The Value It Adds

Quality problems discovered late are vastly more expensive to fix than problems discovered early. The Quality Management agent shifts the quality conversation from a last-minute gate check to a continuous monitoring activity — tracking quality metrics throughout delivery and alerting the team when trends suggest the quality gate will not be met before they actually reach it.

For organisations operating in regulated sectors where quality evidence is required for audit purposes, the combination of structured quality plans, traceable test records, and formal review documentation provides a ready-made evidence base for compliance and assurance reviews.

---

## How It Connects to Other Agents

The Quality Management agent receives requirements from **Agent 08** and provides quality gate assessments to **Agent 09 — Lifecycle and Governance**. For agile projects, it connects to **Agent 10 — Schedule and Planning** for sprint definition-of-done tracking. Quality metrics feed into **Agent 22 — Analytics and Insights** for portfolio-level quality reporting. Release readiness assessments for **Agent 18 — Release and Deployment** depend on quality gate status from this agent.
