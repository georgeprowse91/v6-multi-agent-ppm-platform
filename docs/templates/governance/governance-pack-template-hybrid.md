# Governance Charter (Hybrid)

## Purpose
Establish the governance framework for a hybrid project by defining decision rights, oversight
structure, escalation paths, and reporting cadence across stage-gate and iterative delivery.

## Audience
Executive Sponsor, Steering Committee, PMO Lead, Program Manager, Delivery Lead, Compliance Officer.

## Inputs
- Hybrid charter (`docs/templates/governance/hybrid-charter-hybrid.md`).
- Decision log (`docs/templates/governance/decision-log-hybrid.md`).
- Communications plan (`docs/templates/communications/communications-plan-cross.md`).
- Change request (`docs/templates/change/change-request-cross-var1.md`).

---

## 1. Document Information
| Item | Details |
| --- | --- |
| Project name |  |
| Project manager |  |
| Sponsor |  |
| Version |  |
| Status | Draft / Approved / Active |
| Owner |  |
| Last updated |  |

## 2. Governance Overview
### 2.1 Purpose
Define oversight, accountability, and decision pathways that balance formal stage gates with
iterative delivery autonomy.

### 2.2 Scope
Governance applies to:
- Decision-making authority and approval thresholds.
- Escalation procedures and response SLAs.
- Reporting requirements and steering forums.
- Risk, issue, and change control.
- Compliance, audit, and quality gates.

### 2.3 Governance Objectives
- Align delivery to business strategy and value outcomes.
- Provide transparent accountability and decision rights.
- Enable rapid escalation and issue resolution.
- Maintain compliance with regulatory and enterprise standards.
- Sustain stakeholder engagement and visibility.

## 3. Governance Structure
```
Executive Steering Committee
         ↓
Project Steering Committee
         ↓
Project Manager / Delivery Lead
         ↓
Cross-functional Delivery Squads
```

### 3.1 Governance Bodies
**Executive Steering Committee**
- **Purpose:** Strategic oversight, portfolio alignment, funding decisions.
- **Authority:** Project continuation/termination, major budget approvals.
- **Membership:** Executive sponsor, senior leaders, finance representative.
- **Cadence:** Quarterly or as needed.

**Project Steering Committee**
- **Purpose:** Scope, schedule, and risk oversight.
- **Authority:** Approve major scope changes, escalate risks, resolve cross-team blockers.
- **Membership:** Sponsor, business owners, PMO, delivery lead.
- **Cadence:** Monthly.

**PMO / Governance Office**
- **Purpose:** Standards, assurance, and audit readiness.
- **Authority:** Compliance checks, gating readiness, reporting quality.
- **Cadence:** As needed.

## 4. Roles & Responsibilities
| Role | Responsibilities | Decision Authority | Escalation Path |
| --- | --- | --- | --- |
| Executive Sponsor | Strategic alignment, funding advocacy, final escalation. | Approve major investment changes. | Executive steering committee. |
| Project Sponsor | Business case ownership, stakeholder engagement. | Approve resources and priority shifts. | Executive sponsor. |
| Project Manager | Delivery execution, reporting, day-to-day decisions. | Approve minor changes and risks. | Project sponsor. |
| Delivery Lead / Scrum Master | Iteration execution, impediment removal. | Tactical delivery decisions. | Project manager. |
| Product Owner | Value prioritization, backlog governance. | Approve scope refinements within iteration. | Project manager. |
| Risk Owner | Risk identification, mitigation, reporting. | Recommend risk responses. | Project manager. |
| PMO Lead | Governance compliance, audit readiness. | Gate readiness sign-off. | Steering committee. |

## 5. Decision-Making Framework
### 5.1 Decision Authority Matrix
| Decision Type | Project Manager | Sponsor | Steering Committee | Executive Committee |
| --- | --- | --- | --- | --- |
| Daily operations | Approve | Informed | - | - |
| Resource allocation (<$X) | Approve | Informed | - | - |
| Resource allocation (>$X) | Recommend | Approve | Informed | - |
| Scope changes (minor) | Approve | Informed | - | - |
| Scope changes (major) | Recommend | Recommend | Approve | Informed |
| Budget changes (<Y%) | Recommend | Approve | Informed | - |
| Budget changes (>Y%) | Recommend | Recommend | Approve | Informed |
| Schedule changes (<Z weeks) | Approve | Informed | - | - |
| Schedule changes (>Z weeks) | Recommend | Recommend | Approve | Informed |
| Risk responses (high impact) | Recommend | Approve | Informed | - |
| Project continuation | Recommend | Recommend | Approve | Informed |
| Project termination | Recommend | Recommend | Recommend | Approve |

### 5.2 Decision Process
1. **Identify:** Document decision need and context.
2. **Analyze:** Assess impact, options, and trade-offs.
3. **Recommend:** Provide preferred option with rationale.
4. **Review:** Gather stakeholder input and dependencies.
5. **Decide:** Approve in the appropriate forum.
6. **Record:** Update decision log and action owners.
7. **Communicate:** Inform affected stakeholders.
8. **Monitor:** Track outcomes and adjust as needed.

## 6. Escalation Procedures
### 6.1 Escalation Criteria
- Impact exceeds cost/schedule thresholds.
- Resolution requires authority beyond delivery team.
- Compliance or security risk exposure.
- Cross-functional dependency conflicts.

### 6.2 Escalation Matrix
| Level | Authority | Trigger | Response Time |
| --- | --- | --- | --- |
| 1 | Project Manager | Day-to-day issues | 24 hours |
| 2 | Project Sponsor | Resource or vendor blockers | 48 hours |
| 3 | Steering Committee | Major scope/budget variance | 1 week |
| 4 | Executive Committee | Strategic or viability decisions | 2 weeks |

### 6.3 Escalation Process
1. Document issue, impact, and attempted resolutions.
2. Submit escalation request to next authority level.
3. Track response and decision in issue log.
4. Communicate decision and implement resolution.

## 7. Reporting & Communication
| Report | Audience | Frequency | Owner | Notes |
| --- | --- | --- | --- | --- |
| Executive dashboard | Executive committee | Monthly | Project manager | Focus on value, risks, decisions. |
| Steering update | Steering committee | Bi-weekly | Project manager | Includes scope, budget, risks. |
| Sprint review | Delivery team + stakeholders | Sprint end | Delivery lead | Demo + backlog impacts. |
| Risk & issue summary | PMO | Weekly | Risk owner | Top exposure + mitigations. |

## 8. Change Control
1. **Submit change request** using the change request template.
2. **Assess impact** on scope, schedule, cost, quality, and risk.
3. **Approve** based on decision matrix thresholds.
4. **Update** baselines and change log.
5. **Communicate** changes to delivery teams and stakeholders.

## 9. Performance Management
| KPI | Target | Measurement | Cadence | Owner |
| --- | --- | --- | --- | --- |
| Schedule performance (SPI) |  | Earned value | Monthly | PM |
| Cost performance (CPI) |  | Earned value | Monthly | Finance |
| Quality defect rate |  | Defects per release | Monthly | QA |
| Stakeholder satisfaction |  | Survey score | Quarterly | PMO |
| Delivery predictability |  | Objective achievement | Monthly | Delivery lead |

## 10. Risk & Issue Governance
- **Risk ownership:** named owners per category.
- **Escalation thresholds:** defined in escalation matrix.
- **Issue SLAs:** severity-based response and resolution timelines.
- **Reporting:** risk/issue dashboards aligned to governance cadence.

## 11. Quality Assurance
- **Quality gates:** stage-gate readiness and iteration exit criteria.
- **Deliverable reviews:** peer review, QA sign-off, stakeholder acceptance.
- **Compliance audits:** scheduled evidence review and remediation tracking.

## 12. Document Control
| Version | Date | Author | Changes |
| --- | --- | --- | --- |
|  |  |  |  |

## 13. Governance Review & Improvement
- **Monthly governance check:** confirm decision and escalation adherence.
- **Quarterly process review:** optimize forums, reporting, and gate criteria.
- **Annual governance refresh:** align with strategy and policy changes.

---

## Appendix A: Gate Checklist
| Gate | Required Inputs | Evidence | Approver | Status |
| --- | --- | --- | --- | --- |
| Initiation | Charter, funding |  |  |  |
| Planning | Milestones, risks |  |  |  |
| Delivery | Sprint readiness, change log |  |  |  |
| Integration | Release readiness, QA sign-off |  |  |  |
| Closure | Closure report, handover |  |  |  |

## Appendix B: Governance Artefacts
- Decision log (`docs/templates/governance/decision-log-hybrid.md`).
- Risk register (`docs/templates/risk/integrated-risk-register-hybrid.xlsx`).
- Communications plan (`docs/templates/communications/communications-plan-cross.md`).
- Change log (`docs/templates/change/change-log-cross.md`).

## Completion Checklist
- [ ] Governance structure and decision rights documented.
- [ ] Escalation criteria and response times defined.
- [ ] Reporting cadence agreed with stakeholders.
- [ ] Gate checklist completed with evidence links.

## Acceptance Criteria
- Decision rights and escalation paths are clear and approved.
- Governance reporting supports stage-gate and sprint visibility.
- Evidence for gate approvals is documented and traceable.
