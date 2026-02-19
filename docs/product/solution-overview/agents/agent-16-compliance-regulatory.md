# Agent 16 — Compliance and Regulatory

**Category:** Delivery Management
**Role:** Regulatory Framework Manager and Compliance Monitor

---

## What This Agent Is

The Compliance and Regulatory agent ensures that every project on the platform is managed in accordance with the regulatory frameworks and internal policies that apply to it. It translates abstract compliance obligations into concrete, project-specific requirements; monitors adherence throughout delivery; maintains the evidence needed to demonstrate compliance; and prepares for and supports audit processes.

For organisations operating in regulated sectors — financial services, government, healthcare, defence — compliance is not an optional feature. It is a condition of operation. This agent makes compliance systematic and demonstrable rather than sporadic and anecdotal.

---

## What It Does

**It manages regulatory frameworks.** The agent holds a library of regulatory and policy frameworks relevant to the organisation's operations. Built-in frameworks include the Australian Privacy Act 1988 (APPs), APRA CPS 234, ISO 27001, the Australian Government's Information Security Manual (ASD ISM), and the Protective Security Policy Framework (PSPF). Additional frameworks can be configured by the organisation. Each framework is broken down into its constituent control requirements, which the agent can map to individual projects.

**It defines and maps controls.** For each regulatory requirement, the agent defines the specific control that must be implemented — who must do what, by when, and with what evidence — and maps those controls to the relevant projects, workstreams, or activities. This mapping ensures that each project team knows precisely which compliance obligations apply to their work and what they need to do to satisfy them.

**It conducts compliance assessments.** Periodically, or at governance gate points, the agent assesses each project against its mapped control requirements. The assessment evaluates whether each control has been implemented, whether the required evidence exists, and whether the control has been tested. The result is a compliance scorecard that shows which obligations are met, which are partially met, and which are outstanding.

**It tests controls.** Beyond assessment, the agent supports formal control testing — verifying that a control not only exists in policy but is operating effectively in practice. It records the test approach, the evidence reviewed, the testing outcome, and any exceptions identified.

**It manages the evidence store.** For each control, the agent maintains a collection of evidence snapshots — documents, records, screenshots, or other artefacts that demonstrate the control is in place and operating. Evidence is timestamped, version-controlled, and linked to the specific control and project it relates to. This evidence store is the primary resource for audit preparation.

**It prepares for and supports audits.** When an audit is approaching, the agent prepares an audit readiness package — a structured collection of the evidence, assessments, and control test results that the auditor will need. It tracks the status of audit preparation activity and identifies any evidence gaps that need to be addressed before the audit. During the audit, it provides a structured record of audit queries and responses.

**It monitors regulatory changes.** Regulations change. The agent is designed to monitor for changes to the regulatory frameworks it manages and flag updates that may require new controls to be implemented or existing ones to be revised. This ensures that the compliance picture remains current as the regulatory environment evolves.

**It verifies release compliance.** For technology projects, the agent performs a compliance verification before release — checking that all relevant security scans have been completed, data privacy requirements have been addressed, audit logging is in place, deployment checks have passed, and quality testing is sufficient — providing a compliance clearance for the release to proceed.

---

## How It Works

The agent maintains its control catalogue in a structured internal registry. A simple rules engine evaluates compliance evidence against the defined criteria for each control: whether required documents exist, whether evidence has been uploaded, whether controls have been tested, whether audit logs are present, whether risk mitigations are documented. The rules engine produces a compliance score that is used in the compliance dashboard and stage-gate assessments.

The agent integrates with GRC systems — ServiceNow and RSA Archer — for organisations that manage enterprise compliance programmes through those platforms, ensuring project-level compliance data is visible in the broader enterprise governance picture.

---

## What It Uses

- Built-in regulatory framework library: Privacy Act 1988, APRA CPS 234, ISO 27001, ASD ISM, PSPF
- Configurable additional frameworks and control definitions
- A compliance rule engine for automated assessment against evidence
- GRC system integrations: ServiceNow, RSA Archer
- Document management integration: SharePoint for evidence storage
- Agent 03 — Approval Workflow for audit preparation and compliance approvals
- Agent 09 — Lifecycle and Governance for gate compliance assessments
- The platform's immutable audit log as a compliance evidence source
- The platform's event bus for compliance status events

---

## What It Produces

- **Regulatory framework register**: the library of applicable frameworks and their control requirements
- **Control mapping**: the specific controls mapped to each project and their obligations
- **Compliance assessment reports**: scored assessments of each project against its controls
- **Control test records**: evidence of formal control testing with outcomes and exceptions
- **Evidence snapshots**: timestamped, version-controlled evidence linked to specific controls
- **Audit readiness package**: structured evidence collection for audit preparation
- **Regulatory change alerts**: notifications when monitored frameworks are updated
- **Release compliance clearance**: pre-release verification that compliance requirements are satisfied
- **Compliance dashboard**: real-time view of overall compliance posture across the project

---

## How It Appears in the Platform

The compliance view is accessible from the Compliance activity in the **Methodology Map** navigation. The compliance dashboard in the **Dashboard Canvas** shows the overall compliance posture — which frameworks apply, what percentage of controls are satisfied, and which items require attention. The evidence store and control mapping are available in the **Spreadsheet Canvas** for detailed review.

Compliance gate assessments are surfaced at the relevant stage gates in the methodology map — a project cannot advance past a compliance gate without the agent confirming that the required controls have been satisfied.

The assistant panel supports compliance queries: "Are we compliant with APRA CPS 234?" "What evidence is missing for our next audit?" "Which controls apply to this project?"

---

## The Value It Adds

Compliance failures in regulated industries carry serious consequences — regulatory sanctions, financial penalties, reputational damage, and operational disruption. Most organisations manage compliance reactively, discovering gaps when audits uncover them. The Compliance and Regulatory agent shifts this to a proactive posture: controls are mapped at the start of the project, evidence is collected continuously, gaps are identified in advance, and audit preparation is a structured, evidence-backed process rather than a last-minute scramble.

For PwC-delivered programmes, this agent provides a ready-made compliance evidence framework that can be configured to the client's regulatory context and used as the basis for regulatory assurance reporting.

---

## How It Connects to Other Agents

The Compliance and Regulatory agent draws evidence from the platform's immutable audit log, from quality test records from **Agent 14**, and from risk registers from **Agent 15**. Compliance gate assessments are provided to **Agent 09 — Lifecycle and Governance**. Release compliance clearance is provided to **Agent 18 — Release and Deployment**. Compliance posture data feeds into **Agent 22 — Analytics and Insights** for portfolio-level compliance reporting.
