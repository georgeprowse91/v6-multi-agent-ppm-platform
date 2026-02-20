> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 13 — Vendor and Procurement Management

**Category:** Delivery Management
**Role:** Vendor Lifecycle and Procurement Coordinator

---

## What This Agent Is

The Vendor and Procurement Management agent handles every aspect of the supplier and procurement relationship within a project or programme — from identifying a need for external capability through to contract management, purchase order processing, invoice reconciliation, and ongoing vendor performance tracking.

It is one of the most comprehensive agents in the platform, managing a process that in most organisations spans multiple teams (project management, procurement, legal, finance) and multiple systems (sourcing tools, contract management, ERP). The agent unifies this fragmented process into a single, governed, transparent workflow.

---

## What It Does

**It onboards vendors.** When a new supplier needs to be engaged, the agent manages the onboarding process: capturing vendor details, running risk assessments (including credit checks and sanctions screening), validating that the vendor meets the organisation's procurement standards, and creating a vendor record in the platform and connected procurement systems. It uses Azure Form Recognizer to extract structured data from submitted vendor documents, reducing manual data entry.

**It manages procurement requests.** When a project needs to buy something — a service, a product, a licence, a consultancy engagement — the project team raises a procurement request through the platform. The agent classifies the request by category and complexity, validates it against the available budget (checking with Agent 12), and routes it through the appropriate procurement pathway: a simple purchase for small items, a competitive quotation for medium-value purchases, or a formal RFP process for significant engagements.

**It generates Requests for Proposal.** For competitive procurement, the agent drafts a Request for Proposal (RFP) document, drawing on the project's scope definition and the procurement request to specify the requirement clearly. The RFP is stored in the document canvas and can be reviewed and edited before being issued to shortlisted suppliers.

**It manages proposal evaluation.** When proposals are received from vendors, the agent coordinates the evaluation process — scoring each proposal against predefined criteria (technical capability, commercial terms, delivery approach, risk profile) and consolidating the scores into a comparative evaluation matrix. It uses ML-based vendor scoring to supplement the structured evaluation with a broader capability and risk assessment based on the vendor's historical performance and market data.

**It manages contracts.** Once a vendor is selected, the agent manages the contract lifecycle: creating the contract record from negotiated terms, tracking key dates (commencement, renewal, expiry), managing variations to contract terms, and maintaining a complete contract history. It uses Azure Form Recognizer to extract structured fields from contract documents, reducing the risk of important terms being missed.

**It creates and tracks purchase orders.** Approved procurement commitments result in purchase orders that are created in the platform and synchronised to connected ERP systems (SAP, Oracle, NetSuite). The agent tracks the status of each purchase order — raised, acknowledged, delivered, and closed — and links purchase orders to the corresponding contracts and budget allocations.

**It processes invoices.** As vendor invoices are received, the agent performs three-way matching — verifying that the invoice amount, quantity, and supplier details match the corresponding purchase order and delivery receipt. Matched invoices are routed for payment approval; mismatched invoices are flagged for review with the specific discrepancy identified.

**It tracks vendor performance.** Throughout the engagement, the agent monitors vendor performance against contractual commitments — delivery timescales, quality standards, SLA compliance. It produces vendor scorecards that can be used in future procurement evaluation and maintains a performance history that informs decisions about whether to re-engage a vendor on future work.

---

## How It Works

The agent integrates with enterprise procurement systems — SAP Ariba, Coupa, Oracle Procurement, Microsoft Dynamics — for bidirectional data flow, as well as with the platform's financial management and approval workflow agents. A machine learning-based vendor scoring model supplements structured evaluation criteria with pattern-based assessments of vendor capability and risk.

---

## What It Uses

- The project's budget from Agent 12 for financial validation of procurement requests
- The project's scope definition from Agent 08 for RFP drafting
- Integrations with SAP Ariba, Coupa, Oracle Procurement, Microsoft Dynamics 365
- Azure Form Recognizer for document data extraction
- ML-based vendor scoring model for capability and risk assessment
- Risk database client for credit and sanctions screening
- Agent 03 — Approval Workflow for procurement approvals and contract sign-off
- The event bus for publishing procurement lifecycle events
- ERP integrations (SAP, Oracle, NetSuite) for purchase order synchronisation

---

## What It Produces

- **Vendor records**: onboarded, validated supplier profiles with risk assessment results
- **Procurement requests**: categorised, budget-validated requirements ready for sourcing
- **RFP documents**: structured requests for proposal ready for issue
- **Proposal evaluation matrix**: scored comparison of vendor proposals
- **Contract records**: structured contract data with key dates, terms, and variation history
- **Purchase orders**: approved commitments synchronised to ERP systems
- **Invoice matching results**: three-way match outcomes with discrepancy flags
- **Vendor scorecards**: performance assessments against contractual commitments
- **Procurement dashboard**: pipeline view of all active procurement activities

---

## How It Appears in the Platform

Procurement activity is accessible from the relevant stage of the methodology map — the Procurement or Execution stage, depending on the project type. The **Document Canvas** holds RFP documents, evaluation matrices, and contracts. Purchase orders and invoice status are tracked in the **Spreadsheet Canvas**, providing a tabular view of all commitments and their payment status.

The vendor scorecard is visible from the vendor record in the platform, and can be surfaced in the assistant panel: "How has Vendor X performed on this project?" The procurement pipeline — all active sourcing activities with their current status — is accessible from the project dashboard.

Approval requests for procurement decisions — vendor selection, contract sign-off, invoice approval — appear in the **Approvals** page, routed by the Approval Workflow agent to the appropriate reviewers.

---

## The Value It Adds

Procurement processes in project environments are often poorly governed — RFPs drafted informally, vendor selection decisions poorly documented, contracts filed and forgotten, invoices paid without proper matching. The Vendor and Procurement Management agent applies consistent process governance to every procurement activity, regardless of scale.

For organisations with significant third-party spend, the combination of automated three-way invoice matching, structured vendor performance tracking, and integration with ERP systems delivers meaningful financial control — reducing the risk of overpayment, duplicate payment, and contract non-compliance.

---

## How It Connects to Other Agents

The Vendor and Procurement agent draws on budget data from **Agent 12** and scope context from **Agent 08**. All approval decisions are managed by **Agent 03 — Approval Workflow**. Vendor performance data feeds into **Agent 22 — Analytics and Insights** for portfolio-level supplier reporting. Contracts and procurement records contribute to the compliance evidence tracked by **Agent 16 — Compliance and Regulatory**.
