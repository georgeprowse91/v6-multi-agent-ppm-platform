# Schedule Risk Analysis

## Purpose
Provide a structured approach to identify, quantify, and mitigate schedule risks so stakeholders have realistic completion expectations and contingency plans.

## Audience
Project Manager, Scheduler, Risk Manager, PMO, Delivery Leads, Sponsors.

## Inputs
- Schedule management plan (`docs/templates/schedule/schedule-management-plan-template-cross.md`).
- Project schedule template (`docs/templates/schedule/project-schedule-var2-template-cross.md`).
- Risk management plan (`docs/templates/risk/risk-management-plan-template-cross.md`).
- Risk register (`docs/templates/risk/risk-register-waterfall.xlsx` or `docs/templates/risk/integrated-risk-register-hybrid.xlsx`).

## 1. Schedule Risk Overview
Describe the scope of the schedule risk analysis (phases covered, critical milestones, and decision points).

## 2. Risk Identification
Capture sources of schedule risk and assumptions.

### Risk Sources Checklist
- **Resource risks:** staffing levels, skill gaps, productivity variability.
- **Technical risks:** integration complexity, tooling instability, rework probability.
- **External dependencies:** vendors, regulatory approvals, third-party deliverables.
- **Environmental risks:** weather, political/regional disruptions, market volatility.
- **Organizational risks:** budget constraints, priority shifts, scope changes.

### Initial Risk Capture
| Risk ID | Description | Source Category | Trigger/Indicator | Affected Activities | Owner |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

## 3. Risk Assessment
Define how probability and impact are quantified and linked to schedule variance.

### Probability and Impact Scales
| Rating | Probability Definition | Impact Definition (Days) |
| --- | --- | --- |
| 1 |  |  |
| 2 |  |  |
| 3 |  |  |
| 4 |  |  |
| 5 |  |  |

### Exposure Calculation
- **Risk exposure formula:** Probability × Impact (days).
- **Ranking method:** Sort by exposure and critical path sensitivity.

## 4. Quantitative Analysis Techniques
Select the methods that best fit schedule complexity.

### Monte Carlo Simulation
- **Inputs:** duration distributions, correlations, and risk events.
- **Outputs:** completion confidence intervals, P50/P80 dates, criticality index.
- **Tooling:** @RISK for Project, Pertmaster, or equivalent.

### Sensitivity Analysis
- **Tornado analysis:** rank activities with highest impact on completion variance.
- **Criticality index:** percent of simulations where a task is on critical path.
- **Sensitivity ratio:** variance contribution by activity group.

### Three-Point Estimation (PERT)
| Activity | Optimistic | Most Likely | Pessimistic | PERT Duration | Std Dev |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

**PERT Duration Formula:** (Optimistic + 4×Most Likely + Pessimistic) ÷ 6.

## 5. Mitigation and Response Planning
Define strategies per high-exposure risks.

| Risk ID | Response Strategy (Avoid/Mitigate/Transfer/Accept) | Action Plan | Contingency/Buffer | Owner | Due Date |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

### Buffer Management
- **Project/phase buffers:** size based on exposure or Monte Carlo percentile.
- **Feeding buffers:** protect critical path from non-critical delays.
- **Buffer consumption tracking:** define thresholds (green/amber/red).

## 6. Schedule Risk Views & Reporting
Describe how risk insights will be shared with stakeholders.

### Risk Register View
- Include: task, probability, impact, exposure, category, owner.
- Sort: exposure descending, then criticality index.

### Executive Dashboard Metrics
- Completion probability (P50/P80).
- Top schedule risks by exposure.
- Buffer burn rate vs. plan.
- Risk trend over time.

## 7. Monitoring & Review Cadence
- **Weekly:** update probability/impact for top risks and critical path shifts.
- **Monthly:** refresh simulations, update buffers, adjust mitigation plans.
- **Gate reviews:** reassess schedule risk at phase transitions.

## 8. Implementation Checklist
### Initial Setup
- [ ] Confirm schedule scope, baseline, and critical milestones.
- [ ] Define probability/impact scales and exposure formula.
- [ ] Establish simulation inputs and assumptions.

### Analysis & Response
- [ ] Conduct risk identification workshop.
- [ ] Run qualitative ranking and PERT estimates.
- [ ] Execute Monte Carlo simulation (if applicable).
- [ ] Define buffers and mitigation actions.

### Monitoring & Control
- [ ] Set reporting cadence and dashboard metrics.
- [ ] Assign owners for top risks and mitigations.
- [ ] Track buffer consumption and update schedule forecasts.

## Acceptance Criteria
- Schedule risks are ranked by exposure and criticality.
- Quantitative analysis supports confidence-based completion dates.
- Mitigation plans and buffers are documented and owned.
