# Requirements Traceability Matrix (RTM)

## Document Control
| Field | Value |
| --- | --- |
| Document Title | Requirements Traceability Matrix |
| Project Name | [Project Name] |
| Document ID | RTM-[Project ID]-[Version] |
| Version | 1.0 |
| Status | [Draft/Under Review/Approved/Final] |
| Prepared By | [Name, Title] |
| Preparation Date | YYYY-MM-DD |
| Last Updated By | [Name, Title] |
| Last Revision Date | YYYY-MM-DD |
| Approved By | [Name, Title] |
| Approval Date | YYYY-MM-DD |

## Overview
The RTM maps requirements to design, implementation, and verification artifacts to ensure every
requirement is delivered, tested, and traceable throughout the lifecycle.

**Purpose**
- Track requirements from inception through delivery and acceptance.
- Validate completeness of design, build, and test coverage.
- Support impact analysis for change requests.
- Maintain an audit trail for compliance and quality assurance.

**Scope**
- Functional, non-functional, business, technical, and compliance requirements.
- Integration and interface requirements.
- Requirements derived from SOW, stakeholder input, regulations, architecture, and program goals.

## Requirements Taxonomy
### Requirement Types
- **BR**: Business Requirement
- **FR**: Functional Requirement
- **NFR**: Non-Functional Requirement
- **TR**: Technical Requirement
- **CR**: Compliance/Regulatory Requirement
- **IR**: Interface Requirement
- **SR**: Security Requirement
- **PR**: Performance Requirement
- **UR**: Usability Requirement

### Priority Definitions
- **Critical**: Must-have; project cannot proceed without this requirement.
- **High**: Important; should be included in the current release.
- **Medium**: Desirable; can be deferred if necessary.
- **Low**: Nice-to-have; future consideration.

### Status Definitions
- **Proposed**: Identified but not yet approved.
- **Approved**: Baselined and authorized for delivery.
- **In Design**: Addressed in design artifacts.
- **In Development**: Implementation in progress.
- **In Testing**: Verification in progress.
- **Completed**: Implemented and tested.
- **Verified**: Validated and accepted.
- **Deferred**: Postponed to future release.
- **Cancelled**: Removed from scope.

## RTM Matrix
### Header Guidance
- **Req ID**: Unique requirement identifier.
- **Requirement Description**: Clear, testable statement.
- **Source**: Origin of requirement (SOW, stakeholder, regulation, etc.).
- **Type**: Requirement category.
- **Priority**: Critical/High/Medium/Low.
- **Status**: Current lifecycle state.
- **Design Reference**: Design document/section.
- **Implementation**: Code module/component.
- **Test Case ID**: Test case(s) validating requirement.
- **Verification Method**: Inspection, testing, demonstration, analysis.
- **Acceptance Criteria**: Objective success criteria.
- **Assigned To**: Owner responsible for delivery.
- **Target Date** / **Actual Date**: Planned vs. actual completion.
- **Comments/Notes**: Risks, dependencies, or clarifications.

| Req ID | Requirement Description | Source | Type | Priority | Status | Design Reference | Implementation | Test Case ID | Verification Method | Acceptance Criteria | Assigned To | Target Date | Actual Date | Comments/Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | [Example: System shall authenticate users via SSO] | [SOW 3.1] | FR | Critical | Approved | [Design-Auth-001] | [Module-Auth] | [TC-001] | Testing & Demo | [SSO login successful] | [Owner] | YYYY-MM-DD |  |  |
| REQ-002 | [Example: Response time ≤ 2 seconds] | [Stakeholder] | NFR | High | In Development | [Design-Perf-001] | [Perf Module] | [TC-003] | Performance Test | [95% of requests ≤ 2s] | [Owner] | YYYY-MM-DD |  |  |
| REQ-003 | [Add additional requirements] |  |  |  |  |  |  |  |  |  |  |  |  |  |

## Detailed Requirement Specs (Optional)
Use this section for high-impact or complex requirements that need expanded context.

### REQ-001: [Requirement Title]
**Full Description:** [Detailed requirement statement.]

**Business Rationale:** [Why this requirement exists.]

**Acceptance Criteria**
1. [Criterion 1]
2. [Criterion 2]
3. [Criterion 3]

**Dependencies:** [Systems, teams, approvals, tools.]

**Assumptions:** [Assumptions impacting delivery.]

**Risks:** [Potential issues and mitigations.]

## Coverage Analysis
### Coverage Summary
| Category | Total | Completed | In Progress | Not Started | Coverage % |
| --- | --- | --- | --- | --- | --- |
| Business | [#] | [#] | [#] | [#] | [%] |
| Functional | [#] | [#] | [#] | [#] | [%] |
| Non-Functional | [#] | [#] | [#] | [#] | [%] |
| Technical | [#] | [#] | [#] | [#] | [%] |
| Security | [#] | [#] | [#] | [#] | [%] |
| **Total** | **[#]** | **[#]** | **[#]** | **[#]** | **[%]** |

### Priority Coverage
| Priority | Total | Completed | In Progress | Not Started | Coverage % |
| --- | --- | --- | --- | --- | --- |
| Critical | [#] | [#] | [#] | [#] | [%] |
| High | [#] | [#] | [#] | [#] | [%] |
| Medium | [#] | [#] | [#] | [#] | [%] |
| Low | [#] | [#] | [#] | [#] | [%] |
| **Total** | **[#]** | **[#]** | **[#]** | **[#]** | **[%]** |

## Change Management
### Change Request Impact Analysis
| Change Request ID | Affected Requirements | Impact Assessment | Effort Estimate | Risk Assessment | Approval Status |
| --- | --- | --- | --- | --- | --- |
| CR-001 | [REQ-003, REQ-007] | [Impact summary] | [Hours/points] | [Risk level] | [Pending/Approved] |

### Requirements Change Log
| Date | Req ID | Change Description | Reason | Changed By | Approved By | Impact |
| --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | REQ-001 | [Change summary] | [Reason] | [Name] | [Name] | [Impact] |

## Testing Coverage
### Test Case Mapping
| Test Case ID | Test Case Description | Requirements Covered | Test Type | Test Status | Pass/Fail | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| TC-001 | [SSO login success] | REQ-001 | Functional | Completed | Pass |  |
| TC-002 | [Add test cases] | REQ-XXX | [Type] | [Status] | [Result] |  |

### Test Coverage Metrics
- **Total Requirements:** [#]
- **Requirements with Test Cases:** [#]
- **Test Coverage Percentage:** [%]
- **Tests Passed:** [#]
- **Tests Failed:** [#]
- **Tests Pending:** [#]

## Validation and Verification
### Verification Methods
| Method | Description | Applicable Requirements |
| --- | --- | --- |
| Inspection | Review of documentation and code | [List/All] |
| Demonstration | Show system functionality | [Functional] |
| Testing | Execute test cases | [All testable] |
| Analysis | Mathematical or logical proof | [Performance/capacity] |

### Acceptance Criteria Validation
| Req ID | Acceptance Criteria | Validation Method | Validation Status | Validated By | Date |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | [SSO authentication working] | Testing + Demo | Completed | [QA Team] | YYYY-MM-DD |

## SOW Compliance Mapping (Optional)
| SOW Section | SOW Requirement | RTM Requirement(s) | Compliance Status | Deliverable |
| --- | --- | --- | --- | --- |
| 3.1 | [User authentication] | REQ-001 | Compliant | [Auth Module] |

## Risk Assessment
| Risk ID | Risk Description | Affected Requirements | Probability | Impact | Mitigation Strategy |
| --- | --- | --- | --- | --- | --- |
| RISK-001 | [Risk summary] | [REQ-001] | Medium | High | [Mitigation] |

## Reporting and Metrics
### Weekly Status Snapshot
- **Reporting Period:** [Start Date] - [End Date]
- **Total Requirements:** [#]
- **Completed:** [#] ([%])
- **In Progress:** [#] ([%])
- **Not Started:** [#] ([%])

### Quality Metrics
- **Requirements Defect Rate:** [#] defects per [#] requirements
- **Requirements Volatility:** [#] changes per week
- **Test Coverage:** [%] of requirements covered by tests
- **Requirements Completeness:** [%] of planned requirements defined

## Appendices
### Appendix A: Requirements Approval Matrix
| Req ID | Business Analyst | Technical Lead | Security Officer | Project Manager | Customer/Sponsor |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | [Name/Date] | [Name/Date] | [Name/Date] | [Name/Date] | [Name/Date] |

### Appendix B: Requirements Sources
| Source Document | Version | Date | Key Requirements |
| --- | --- | --- | --- |
| [Statement of Work] | [1.2] | YYYY-MM-DD | [REQ-001, REQ-002] |

### Appendix C: Glossary
| Term | Definition |
| --- | --- |
| RTM | Requirements Traceability Matrix |

## Document Revision History
| Version | Date | Author | Changes Made |
| --- | --- | --- | --- |
| 1.0 | YYYY-MM-DD | [Name] | Initial creation |
| 1.1 | YYYY-MM-DD | [Name] | [Summary of changes] |

**Document Status:** [Draft/Under Review/Approved/Final]
**Next Review Date:** YYYY-MM-DD
**Document Owner:** [Project Manager Name]
**Document Location:** [SharePoint/Repo link]

_This RTM is a living document and should be updated throughout the project lifecycle to maintain
traceability from inception through delivery and acceptance._
