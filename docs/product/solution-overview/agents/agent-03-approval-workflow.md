# Agent 03 — Approval Workflow

**Category:** Core Orchestration
**Role:** Governance and Decision Routing

---

## What This Agent Is

The Approval Workflow agent is the platform's governance engine. Wherever a decision needs to be made by a human — approving a business case, signing off a scope change, authorising a vendor contract, granting access to a new resource — this agent manages the entire process from the moment the request is raised through to the moment the decision is recorded.

It ensures that approvals are routed to the right people, that decisions are made within defined timeframes, that reminders and escalations happen automatically, and that every approval decision is permanently recorded with a full audit trail. It is the mechanism through which the platform enforces governance without relying on manual chasing or informal processes.

---

## What It Does

**It creates and manages approval chains.** When an action in the platform requires human sign-off, the Approval Workflow agent creates a structured approval chain — a sequence of approvers, each of whom must review and decide before the process can advance. These chains are role-based: the agent looks at the nature of the request, its risk level, its financial value, and the organisational context to determine who the right approvers are.

**It routes requests to the right people.** Rather than sending every approval to a fixed list of names, the agent routes dynamically. A low-value procurement request goes to a project manager. A high-value contract goes to a finance lead and a programme director. An approval with regulatory implications involves the compliance team. The routing rules are configurable and can be adapted to match any organisation's governance structure.

**It supports delegation.** If a designated approver is unavailable — on leave, outside working hours, or overloaded — the agent supports delegation rules that redirect the approval to an appropriate substitute. Delegation can be configured in advance by the approver or applied automatically based on calendar availability.

**It sends notifications through multiple channels.** When an approval task is created, modified, or overdue, the agent notifies the relevant people. It sends notifications by email, Microsoft Teams, Slack, and push notification — whichever channel the recipient has configured as their preference. Notifications are formatted clearly, include the context needed to make a decision, and contain direct links to the approval task in the platform.

**It escalates automatically.** Every approval task has a deadline. If a decision is not made within the required timeframe, the agent automatically escalates — notifying a senior approver, sending a reminder, or triggering a governance alert. The escalation timeline is calculated dynamically based on the urgency and risk level of the request.

**It records decisions permanently.** Every approval decision — approved, rejected, or deferred — is recorded in the platform's audit log with the identity of the approver, the timestamp, any comments provided, and the outcome. This record cannot be altered and is retained according to the platform's data retention policy.

**It supports digest notifications.** For approvers who handle high volumes of approval tasks, the agent can batch pending items into a single digest notification rather than sending a separate message for each one. This reduces notification fatigue while ensuring nothing is missed.

---

## How It Works

The agent assesses each incoming approval request to determine its risk level and criticality, then uses those assessments to calculate the appropriate escalation timeline and select the correct approval chain. It persists approval state — which tasks are pending, which have been decided, who has been notified — so that the process continues correctly even if the system restarts.

Notifications are generated from localised templates. The platform currently supports English and French notification templates, with the structure to add further languages as required. Accessibility is also addressed: notifications can be delivered in plain text format or HTML with appropriate alt text depending on the recipient's preferences.

The agent integrates with Microsoft Graph to create calendar entries and tasks for approvers, so that approval deadlines appear alongside their other commitments rather than only in the platform.

---

## What It Uses

- Role-based routing rules configured per tenant
- Risk and criticality assessment logic to determine escalation timelines
- Notification templates in multiple languages
- Email, Microsoft Teams, Slack, and push notification channels
- Microsoft Graph for calendar and task integration
- The Azure Service Bus for event publishing
- The platform's audit log for permanent decision recording
- An approval store for persistence of approval state

---

## What It Produces

- **Approval tasks** routed to the relevant approvers with full context
- **Notification messages** across the configured channels, formatted and localised
- **Escalation alerts** when decisions are not made within the required timeframe
- **Decision records** in the audit log for every approval outcome
- **Approval status updates** visible in the platform's Approvals page

---

## How It Appears in the Platform

The Approvals page in the platform provides a complete view of all pending and completed approval tasks. Approvers see a queue of items awaiting their decision, with the relevant context — what is being approved, who raised it, what supporting information is available, and what the deadline is. They can approve, reject or comment from within this view without needing to navigate elsewhere.

The platform also surfaces approval status inline within the relevant workflow context — for example, a project that is waiting for a business case approval will show the pending approval status on its lifecycle stage in the methodology map.

---

## The Value It Adds

The Approval Workflow agent replaces the informal, unreliable approval processes that most organisations rely on — emails that get lost, decisions made in meetings with no record, approvals that never happen because nobody followed up. It ensures that every decision that should be made actually gets made, by the right person, within the right timeframe, with a permanent record of the outcome.

For regulated industries, this is not a convenience feature — it is a compliance requirement. The combination of automated routing, escalation, and immutable audit records means organisations can demonstrate their governance processes to auditors and regulators with confidence.

---

## How It Connects to Other Agents

The Approval Workflow agent is called by virtually every other agent in the platform whenever a step in a process requires human authorisation. Requests that originate from the **Business Case and Investment** agent, the **Vendor Procurement** agent, the **Change and Configuration** agent, the **Project Definition and Scope** agent, and many others are routed through Agent 03 when they reach a decision gate. It feeds its outputs — approval decisions and status updates — back to the requesting agent so that the downstream workflow can continue.
