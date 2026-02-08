# Schedule Management Metrics Guide

## Purpose
Provide structured guidance for implementing schedule performance metrics, including Earned Value
Management (EVM) and Critical Path analysis, so project teams can monitor schedule health and make
data-driven decisions.

## Audience
Project Manager, Scheduler, PMO, Finance Analyst, Delivery Leads, Sponsors.

## Inputs
- Schedule management plan (`docs/templates/schedule/schedule-management-plan-template-cross.md`).
- Project schedule template (`docs/templates/schedule/project-schedule-var2-template-cross.md`).
- Schedule risk analysis (`docs/templates/risk/schedule-risk-analysis-var1-template-cross.md`).

---

## 1. Earned Value Management (EVM)

### 1.1 Core Metrics
| Metric | Acronym | Definition | Formula |
| --- | --- | --- | --- |
| Planned Value | PV (BCWS) | Budgeted cost of work scheduled | PV = Planned % Complete × BAC |
| Earned Value | EV (BCWP) | Budgeted cost of work performed | EV = Actual % Complete × BAC |
| Actual Cost | AC (ACWP) | Actual cost incurred | AC = Sum of actual costs |

### 1.2 Variance Metrics
| Metric | Acronym | Formula | Interpretation |
| --- | --- | --- | --- |
| Schedule Variance | SV | EV - PV | Positive = ahead, negative = behind |
| Cost Variance | CV | EV - AC | Positive = under budget |
| Variance at Completion | VAC | BAC - EAC | Expected final variance |

### 1.3 Performance Indices
| Metric | Acronym | Formula | Interpretation |
| --- | --- | --- | --- |
| Schedule Performance Index | SPI | EV ÷ PV | >1 ahead, <1 behind |
| Cost Performance Index | CPI | EV ÷ AC | >1 under budget |
| To-Complete Performance Index | TCPI | (BAC - EV) ÷ (EAC - AC) | Required future performance |

### 1.4 EAC Forecasting Methods
| Method | Formula | Use Case |
| --- | --- | --- |
| EAC₁ | AC + (BAC - EV) | Current variance is atypical |
| EAC₂ | BAC ÷ CPI | CPI expected to continue |
| EAC₃ | AC + [(BAC - EV) ÷ (CPI × SPI)] | CPI and SPI expected to continue |
| EAC₄ | AC + Bottom-up ETC | Detailed re-estimate available |

### 1.5 Implementation Checklist
- [ ] WBS and schedule baseline approved
- [ ] Reporting cadence defined (weekly/bi-weekly/monthly)
- [ ] Measurement method defined (percent complete, weighted milestones)
- [ ] Data owners identified
- [ ] Thresholds for variance escalations set

---

## 2. Critical Path Analysis

### 2.1 Critical Path Definitions
- **Critical path:** Longest sequence of dependent tasks with zero total float.
- **Total float:** Maximum delay without affecting project finish.
- **Free float:** Maximum delay without affecting immediate successors.

### 2.2 Critical Path Metrics
| Metric | Definition | Target |
| --- | --- | --- |
| Critical path length | Total duration of critical tasks | ≤ project deadline |
| Critical ratio | % of tasks on critical path | <20% preferred |
| Near-critical paths | Paths with float ≤ threshold | Monitor closely |
| Schedule risk index | (Critical + near-critical tasks) ÷ total tasks | <30% preferred |

### 2.3 Schedule Compression Options
- **Fast-tracking:** Parallelize tasks at higher risk of rework.
- **Crashing:** Add resources to critical tasks (assess cost impact).
- **Resource smoothing:** Use float to optimize staffing without extending duration.

---

## 3. Performance Interpretation

### 3.1 Thresholds
| Zone | SPI | CPI | Response |
| --- | --- | --- | --- |
| Green | ≥0.95 | ≥0.95 | Maintain course |
| Yellow | 0.90–0.94 | 0.90–0.94 | Investigate drivers |
| Red | <0.90 | <0.90 | Execute corrective action plan |

### 3.2 Trend Analysis
- Use 3- and 6-period rolling averages for SPI/CPI.
- Correlate schedule variance with risk register updates.
- Document root causes and corrective actions.

---

## 4. Reporting and Dashboards

### 4.1 Executive Dashboard KPIs
- SPI and CPI current values with trend arrows.
- Forecast completion date vs. baseline.
- Critical path changes since last report.
- Top 5 schedule risks and mitigation status.

### 4.2 Standard Reporting Pack
| Report | Purpose | Audience | Frequency |
| --- | --- | --- | --- |
| EVM summary | Performance and variance snapshot | Sponsors | Monthly |
| Critical path review | Focus on high-risk tasks | Delivery leads | Weekly |
| Schedule risk summary | Risk posture and mitigations | PMO | Monthly |

---

## 5. Troubleshooting Common Issues

| Issue | Symptoms | Likely Causes | Recommended Actions |
| --- | --- | --- | --- |
| Inconsistent % complete | SPI volatility | No objective measures | Define completion criteria and train team |
| Baseline drift | Sudden performance improvements | Frequent baseline changes | Enforce change control |
| Artificial critical path | Unrealistic critical tasks | Constraints or missing dependencies | Review schedule logic and constraints |

---

## Acceptance Criteria
- EVM and critical path metrics are defined and tracked on a consistent cadence.
- Thresholds and escalation rules are documented.
- Metrics inform corrective actions and governance decisions.
