# Governance Charter (Hybrid)

## Purpose
Define governance structure, decision rights, escalation paths, and reporting requirements for
hybrid delivery.

## Audience
PMO Lead, Program Manager, Compliance Officer, Steering Committee.

## Inputs
- Hybrid charter (`docs/methodology/hybrid/templates/hybrid-charter.md`).
- Decision log (`docs/methodology/hybrid/templates/decision-log.md`).
- Communications plan (`docs/templates/shared/communications-plan.md`).

## 1. Document Information
- **Project name:**
- **Version:**
- **Status:** [Draft/Approved/Active]
- **Owner:**
- **Last updated:**

## 2. Governance Overview
### 2.1 Scope
Describe governance coverage (decision-making, approvals, escalations, reporting, risk, change
control).

### 2.2 Governance Objectives
- Ensure strategic alignment and value delivery.
- Provide clear decision authority and accountability.
- Enable timely escalation and risk resolution.
- Maintain compliance with organizational standards.

## 3. Governance Structure
```
Executive Steering Committee
         ↓
Project Steering Committee
         ↓
Project Manager
         ↓
Delivery Squads
```

### 3.1 Governance Bodies
**Executive Steering Committee**
- Purpose, authority, membership, meeting cadence.

**Project Steering Committee**
- Purpose, authority, membership, meeting cadence.

**PMO / Governance Office**
- Standards, assurance, and escalation support.

## 4. Roles & Responsibilities
| Role | Responsibilities | Decision Authority | Escalation Path |
| --- | --- | --- | --- |
| Executive Sponsor |  |  |  |
| Project Sponsor |  |  |  |
| Project Manager |  |  |  |
| Product Owner |  |  |  |
| Delivery Lead |  |  |  |
| Risk Owner |  |  |  |

## 5. Decision-Making Framework
### 5.1 Decision Authority Matrix
| Decision Type | PM | Sponsor | Steering Committee | Executive Committee |
| --- | --- | --- | --- | --- |
| Daily operations | Approve | Informed | - | - |
| Scope change (minor) | Approve | Informed | - | - |
| Scope change (major) | Recommend | Recommend | Approve | Informed |
| Budget change (<X%) | Recommend | Approve | Informed | - |
| Budget change (>X%) | Recommend | Recommend | Approve | Informed |
| Schedule change (<Y weeks) | Approve | Informed | - | - |
| Schedule change (>Y weeks) | Recommend | Recommend | Approve | Informed |
| Project continuation | Recommend | Recommend | Approve | Informed |
| Project termination | Recommend | Recommend | Recommend | Approve |

### 5.2 Decision Process
1. Identify decision need and document context.
2. Analyze impacts and options.
3. Obtain stakeholder input.
4. Approve in the correct forum.
5. Record in the decision log.
6. Communicate and implement.

## 6. Escalation Procedures
- **Escalation criteria:** scope/budget/schedule thresholds, risk severity, compliance impacts.
- **Response time targets:** define by severity.
- **Escalation owner:** [Role].
- **Reference:** escalation matrix in `docs/templates/shared/communications-plan.md`.

## 7. Reporting & Communication
| Report | Audience | Frequency | Owner |
| --- | --- | --- | --- |
| Executive dashboard | Executive committee | Monthly | PM |
| Steering update | Steering committee | Bi-weekly | PM |
| Sprint review | Delivery team | Sprint end | Delivery lead |
| Risk & issue summary | PMO | Weekly | Risk owner |

## 8. Change Control
- **Change request intake:** Link to change request template.
- **Impact assessment:** Scope/schedule/cost/quality.
- **Approval levels:** defined in decision matrix.
- **Change log:** `docs/templates/shared/change-log.md`.

## 9. Performance Management
| KPI | Target | Cadence | Owner |
| --- | --- | --- | --- |
| Schedule performance (SPI) |  | Monthly | PM |
| Cost performance (CPI) |  | Monthly | Finance |
| Quality defect rate |  | Monthly | QA |
| Stakeholder satisfaction |  | Quarterly | PMO |

## 10. Risk & Issue Governance
- **Risk ownership:** assigned per risk category.
- **Escalation thresholds:** defined and tracked.
- **Issue resolution SLAs:** defined per severity.
- **Risk/issue dashboards:** linked to executive dashboard.

## 11. Quality Assurance
- **Quality gates:** defined per stage gate.
- **Deliverable reviews:** checklist and approvals.
- **Compliance audits:** schedule and evidence storage.

## 12. Document Control
| Version | Date | Author | Changes |
| --- | --- | --- | --- |
|  |  |  |  |

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
- Decision log (`docs/methodology/hybrid/templates/decision-log.md`).
- Risk register (`docs/methodology/hybrid/templates/integrated-risk-register.xlsx`).
- Communications plan (`docs/templates/shared/communications-plan.md`).

## Completion Checklist
- [ ] Governance structure and decision rights documented.
- [ ] Escalation criteria and response times defined.
- [ ] Reporting cadence agreed with stakeholders.
- [ ] Gate checklist completed with evidence links.

## Acceptance Criteria
- Decision rights and escalation paths are clear and approved.
- Governance reporting supports stage-gate and sprint visibility.
- Evidence for gate approvals is documented and traceable.
