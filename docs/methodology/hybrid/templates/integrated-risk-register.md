# Integrated Risk Register (Hybrid)

## Purpose
Provide a unified view of risks across phase gates and sprint delivery cycles, enabling consistent assessment, response planning, and governance reporting.

## Audience
Risk Manager, Project Manager, Delivery Leads, Product Owner, PMO.

## Inputs
- Risk management plan (`docs/templates/shared/risk-management-plan.md`).
- Phase plans and milestone plan (`docs/methodology/hybrid/templates/milestone-plan.xlsx`).
- Sprint/iteration plans (`docs/methodology/agile/templates/iteration-plan.md`).
- Lessons learned (`docs/templates/shared/lessons-learned.md`).

---

## Document Control Information
- **Project/Program Name:**
- **Document Version:**
- **Prepared By:**
- **Preparation Date:**
- **Last Updated By:**
- **Last Revision Date:**

---

## 1. Risk Management Approach
### 1.1 Process Overview
Describe how risks are identified, analyzed, responded to, and monitored across phase gates and sprints.

### 1.2 Roles & Responsibilities
| Role | Responsibilities |
| --- | --- |
| Project Manager | Overall risk governance, escalation, and reporting. |
| Product Owner | Identifies product/backlog risks and prioritization impacts. |
| Delivery Leads | Identify sprint execution risks and mitigation actions. |
| Risk Owner | Implements response actions and reports status. |
| Steering Committee | Reviews high exposure risks and approves responses requiring resources. |

### 1.3 Risk Thresholds
| Risk Score | Category | Action Required |
| --- | --- | --- |
| 15–25 | High | Immediate response plan and escalation. |
| 8–14 | Medium | Mitigation plan and weekly monitoring. |
| 1–7 | Low | Accept or monitor with minimal action. |

---

## 2. Risk Identification & Categorization
### 2.1 Risk Categories
| Category | Description | Examples |
| --- | --- | --- |
| Technical | Architecture, integration, performance, quality. | API failures, scalability issues. |
| Schedule | Timeline, dependencies, critical path. | Vendor delays, unrealistic estimates. |
| Cost | Budget, funding, cost variance. | Cost overruns, inflation impacts. |
| Resource | Capacity, skills, availability. | Key resource attrition. |
| External | Vendor, regulatory, market. | Regulatory changes, supply chain. |
| Organizational | Governance, prioritization, policy. | Leadership change, reprioritization. |
| Change Management | Adoption, training, readiness. | Low user adoption. |
| Scope | Requirements, scope creep. | Ambiguous requirements. |

### 2.2 Risk ID Format
Risk IDs follow `RISK-[Category Code]-[Sequential Number]` (e.g., `RISK-T-001`).

---

## 3. Risk Assessment
### 3.1 Probability Scale
| Score | Level | Probability Range |
| --- | --- | --- |
| 5 | Very High | >90% |
| 4 | High | 70–90% |
| 3 | Medium | 30–70% |
| 2 | Low | 10–30% |
| 1 | Very Low | <10% |

### 3.2 Impact Scale
| Score | Level | Schedule Impact | Cost Impact | Scope/Quality Impact |
| --- | --- | --- | --- | --- |
| 5 | Very High | >2 months | >20% budget | Major scope loss / unacceptable quality |
| 4 | High | 1–2 months | 10–20% budget | Major deliverables affected |
| 3 | Medium | 2–4 weeks | 5–10% budget | Some deliverables impacted |
| 2 | Low | 1–2 weeks | 1–5% budget | Minor impact |
| 1 | Very Low | <1 week | <1% budget | Negligible impact |

### 3.3 Risk Score
**Risk Score = Probability × Impact** (range 1–25). Use the highest impact dimension when multiple impacts apply.

---

## 4. Risk Response Planning
### 4.1 Response Strategies
| Strategy | Description | Example |
| --- | --- | --- |
| Avoid | Eliminate the risk source. | Change solution approach to remove dependency. |
| Transfer | Shift risk to third party. | Insurance or contractual penalties. |
| Mitigate | Reduce probability/impact. | Add testing, buffer, or training. |
| Accept | No action beyond monitoring. | Track low risks with triggers. |
| Escalate | Outside authority/scope. | Policy change risk. |

### 4.2 Secondary Risks
Capture new risks created by mitigation actions and assign owners.

---

## 5. Monitoring & Control
### 5.1 Review Cadence
| Review Type | Frequency | Participants | Purpose |
| --- | --- | --- | --- |
| Sprint Planning | Each sprint | Delivery team | Identify sprint risks. |
| Sprint Review | Each sprint | Team + stakeholders | Review mitigation impact. |
| Monthly Risk Review | Monthly | PMO + leads | Portfolio-level review. |
| Phase Gate Review | As scheduled | Governance group | Escalation/approval decisions. |

### 5.2 Status Definitions
- **Identified**
- **Analyzed**
- **Planned**
- **In Progress**
- **Monitoring**
- **Occurred**
- **Closed**
- **Residual**

---

## 6. Integrated Risk Register
| Risk ID | Description | Category | Phase | Sprint/Iteration | Probability (1–5) | Impact (1–5) | Score | Priority | Response Strategy | Response Actions | Owner | Status | Target Date | Comments |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

---

## 7. Risk History Log
| Date | Risk ID | Change Description | Previous Values | New Values | Changed By | Reason |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

---

## 8. Approval
| Name | Title | Signature | Date |
| --- | --- | --- | --- |
|  |  |  |  |

---

## Completion Checklist
- [ ] Risks captured at both phase and sprint levels.
- [ ] Exposure scores calculated and ranked.
- [ ] Owners and response strategies assigned.
- [ ] Review cadence and escalation paths defined.

## Acceptance Criteria
- Integrated register provides a single view of hybrid risks.
- Exposure and status are current for governance reporting.
- High risks have documented response plans and owners.
