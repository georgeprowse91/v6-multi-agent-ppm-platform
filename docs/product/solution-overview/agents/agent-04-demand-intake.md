> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 04 — Demand and Intake

**Category:** Portfolio Management
**Role:** Project Request Handler

---

## What This Agent Is

The Demand and Intake agent is where every project begins. It is the front door through which ideas, requests, and proposals enter the platform — regardless of which channel they come from or who is submitting them. Its job is to ensure that no request gets lost, that every submission is consistently captured and classified, and that the right people are notified so that the review process can begin promptly.

Before this agent, organisations typically manage demand through email threads, spreadsheets, or manual entry into a PPM tool — processes that are inconsistent, hard to track, and impossible to report on reliably. The Demand and Intake agent replaces all of that with a structured, automated, multi-channel intake process.

---

## What It Does

**It receives requests from multiple channels.** A project request can arrive as a submission through the platform's intake form, a message sent to a connected Slack workspace, an email to a configured address, or a notification from Microsoft Teams. The agent monitors all configured channels and captures submissions from any of them, applying the same processing logic regardless of source.

**It classifies each request automatically.** Once a request is received, the agent analyses its content and assigns it a category — is this a capital project, a technology initiative, a regulatory compliance programme, a change request, or something else? It also estimates the complexity and scale of the request based on the description provided. These classifications feed into the routing and prioritisation logic that determines how the request is handled next.

**It checks for duplicates.** The agent uses semantic similarity analysis to compare each new request against existing demands in the system. If a similar request has already been submitted — perhaps from a different team or through a different channel — the agent flags the potential duplicate so that reviewers can consider whether to consolidate or keep them separate. This prevents the portfolio from filling up with overlapping initiatives.

**It enriches the submission.** Where the submitted information is incomplete, the agent prompts the submitter for missing details or supplements the record with information it can derive from context — the submitting business unit, the relevant portfolio or programme, suggested categorisation, and similar historical projects. This reduces the administrative burden on the intake team and ensures that demand records are complete enough to be usefully reviewed.

**It routes requests for review.** Once a submission has been validated and enriched, the agent triggers a notification to the appropriate reviewers and creates an intake record that appears in the platform's intake queue. Reviewers can see all pending requests, their classifications, and their status from a single view.

**It maintains a pipeline view.** The agent tracks the status of every demand item — submitted, under review, approved for further development, rejected, or converted into a project — and provides a pipeline visualisation that shows where each request sits in the process. This gives portfolio managers visibility into the incoming workload and helps them plan capacity for the review and business case process.

---

## How It Works

The agent uses natural language processing to interpret and classify the text of each submission. It applies a set of validation rules to check that the required fields are present and that the submission meets the minimum information standards needed for a meaningful review. Vector-based embedding is used for duplicate detection — the agent converts each new request into a numerical representation and compares it against the embedded representations of existing demands to find semantically similar submissions.

Event publishing ensures that other parts of the platform — the notification service, the intake approval queue, the portfolio management views — are kept informed as the status of each demand item changes.

---

## What It Uses

- Intake form submissions from the platform's web interface
- Connected Slack, Teams and email channels for multi-channel capture
- Natural language processing for classification and entity extraction
- Semantic embedding and vector search for duplicate detection
- Validation rules to enforce minimum submission standards
- The notification service to alert reviewers of new submissions
- The platform's event bus to publish status changes
- A canonical demand schema to ensure consistent data structure

---

## What It Produces

- **Demand records** in the platform's data store, consistently structured regardless of the channel of origin
- **Classification labels** identifying the request type and estimated complexity
- **Duplicate flags** where semantically similar requests already exist
- **Intake notifications** to configured reviewers
- **Pipeline status updates** as requests move through the review process
- **Enriched submission data** supplementing incomplete requests with inferred context

---

## How It Appears in the Platform

The **Intake Form** page provides a structured submission experience for users raising new project requests. The form collects the key information the platform needs: a description of the initiative, the business problem being addressed, the expected benefits, the requesting business unit, the estimated scale, and any supporting materials.

The **Intake Queue** page gives portfolio managers and reviewers a consolidated view of all submitted requests, organised by status and classification. Each item shows a summary of the request, its classification, its submission date, and any flags raised by the agent (such as duplicate detection). Reviewers can approve, reject, request more information, or convert a request into a full business case from this view.

The **Intake Status** page allows submitters to track the progress of their own requests through the review process without needing to contact the portfolio team.

---

## The Value It Adds

Organisations that manage demand informally typically find that only a fraction of submitted project ideas are properly evaluated — many are lost in email, deprioritised without communication, or never formally reviewed at all. The Demand and Intake agent ensures that every request is captured, every submitter receives a response, and every decision is traceable.

For portfolio managers, having a structured, classified, deduplicated demand pipeline is essential for planning and forecasting. They can see how many requests are in progress, what types of initiative are being proposed, and whether the incoming pipeline aligns with the organisation's strategic priorities — all from a single view.

---

## How It Connects to Other Agents

Once a demand item has been approved for development, the Demand and Intake agent hands off to **Agent 05 — Business Case and Investment Analysis**, which takes the enriched demand record and builds out the financial and strategic case for the initiative. The agent also works with **Agent 03 — Approval Workflow** to manage the review and approval of intake submissions, and surfaces its outputs in the portfolio-level views managed by **Agent 06 — Portfolio Strategy and Optimisation**.
