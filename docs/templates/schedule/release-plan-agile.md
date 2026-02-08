# Release Plan

## Purpose
Define release scope, timing, dependencies, and readiness criteria so stakeholders align on
outcomes, risks, and operational readiness.

## Audience
Product Owner, Release Manager, Engineering Lead, QA Lead, Operations, Security, Stakeholders.

## Inputs
- Sprint plans (`docs/templates/product/sprint-plan-agile.md`).
- Backlog priorities (`docs/templates/product/backlog-template-agile.csv`).
- Risk and change logs.
- Architecture and operational runbooks.

## Definitions
- **Release window:** The target timeframe for deployment and customer rollout.
- **Readiness checklist:** Required criteria for a safe and compliant release.
- **Go/No-Go:** A formal decision point to proceed, delay, or rollback.

## Methodology Gate Alignment
- Agile gate: Sprint Review Gate (`docs/methodology/agile/gates.yaml`).
- Hybrid gate: Release Readiness Gate (`docs/methodology/hybrid/gates.yaml`).

## How to Use
1. Complete the release overview and scope sections before planning sprints.
2. Align feature commitments with backlog priorities and capacity.
3. Validate dependencies, risks, and quality gates with owners.
4. Finalize readiness checklist, communications, and approval workflow.
5. Review and update the plan at each sprint boundary.

## Required Sections
- Release overview
- Vision, goals, and success metrics
- Scope summary and feature commitments
- Schedule and sprint plan
- Dependencies, assumptions, and risks
- Quality and readiness criteria
- Communication plan
- Post-release plan
- Approvals and sign-off

## Release Overview
- **Release name:**
- **Release owner:**
- **Version:**
- **Target window:**
- **Deployment approach:** (phased, big-bang, canary, blue/green)
- **Status:** (draft/in review/approved/active)
- **Review cadence:**

## Vision, Goals, and Success Metrics
### Release Vision
[One-sentence statement describing the value this release will deliver.]

### Release Goals
- **Primary goal:**
- **Secondary goals:**
  - 
  - 

### Success Metrics
| Metric | Target | Measurement Method | Review Frequency | Owner |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Scope Summary
### In Scope
- 
- 

### Out of Scope
- 
- 

### Feature Commitments
| Feature / Epic | Description | Business Value | Target Sprint | Owner | Status | Acceptance Criteria |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

## Stakeholder Information
| Stakeholder | Role | Responsibility | Contact | Engagement Level |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Schedule and Sprint Plan
### Release Schedule
- **Release planning window:**
- **Development window:**
- **Testing window:**
- **Release date:**
- **Post-release support:**

### Sprint Plan
| Sprint | Start Date | End Date | Goal | Planned Stories |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

### Key Milestones
| Milestone | Target Date | Definition of Done | Dependencies |
| --- | --- | --- | --- |
|  |  |  |  |

## Dependencies and Assumptions
- **External dependencies:**
- **Cross-team dependencies:**
- **Assumptions:**

## Quality and Readiness
### Testing Strategy
- **Unit testing:**
- **Integration testing:**
- **User acceptance testing:**
- **Performance testing:**
- **Security review:**

### Quality Gates
| Gate | Criteria | Responsible |
| --- | --- | --- |
| Sprint Review |  |  |
| Release Candidate |  |  |
| Production Ready |  |  |

### Release Readiness Checklist
- [ ] Scope agreed and approved by Product Owner.
- [ ] Security review completed.
- [ ] QA sign-off recorded.
- [ ] Operational runbook updated.
- [ ] Rollback plan validated.
- [ ] Support team briefed.
- [ ] Stakeholders informed.

## Risk and Issue Management
### Release Risks
| Risk ID | Risk Description | Probability | Impact | Mitigation Strategy | Owner |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

### Issues and Escalations
- **Issue log location:**
- **Escalation path:**
- **Decision authority:**

## Communication Plan
| Audience | Channel | Message | Date | Owner |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Go/No-Go Criteria
- [ ] All must-have features complete.
- [ ] Quality gates passed.
- [ ] Performance benchmarks met.
- [ ] Security review complete.
- [ ] Documentation updated.
- [ ] Support team trained.
- [ ] Rollback plan approved.

## Post-Release Plan
### Go-Live Activities
- [ ] Production deployment completed.
- [ ] Monitoring activated and validated.
- [ ] Stakeholder communications sent.
- [ ] Support coverage confirmed.

### Success Measurement
- **Monitoring period:**
- **Key metrics:**
- **Review cadence:**

### Retrospective and Lessons Learned
- **Retrospective date:**
- **Participants:**
- **Top improvements:**

## Approvals
| Approver | Role | Decision | Date |
| --- | --- | --- | --- |
|  |  |  |  |

## Completion Checklist
- [ ] Dependencies and assumptions validated.
- [ ] Communications scheduled.
- [ ] Approvals recorded.
- [ ] Post-release monitoring plan confirmed.

## Data Fields (Machine-Readable)
```yaml
release_plan:
  metadata:
    release_id: "{{release_id}}"
    version: "{{version}}"
    status: "{{status}}"
    last_updated: "{{last_updated}}"
  ownership:
    release_owner: "{{release_owner}}"
    product_owner: "{{product_owner}}"
    engineering_lead: "{{engineering_lead}}"
  schedule:
    target_window: "{{target_window}}"
    release_date: "{{release_date}}"
  quality:
    qa_signoff: "{{qa_signoff}}"
    security_review: "{{security_review}}"
    rollback_plan_owner: "{{rollback_plan_owner}}"
  metrics:
    success_metric_1: "{{success_metric_1}}"
    success_metric_2: "{{success_metric_2}}"
```

## References
- Agile methodology map (`docs/methodology/agile/map.yaml`).
- Release readiness gate criteria (`docs/methodology/agile/gates.yaml`).
