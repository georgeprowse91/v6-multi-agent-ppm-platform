> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 21 — Stakeholder Communications

**Category:** Operations Management
**Role:** Communications Planner and Engagement Manager

---

## What This Agent Is

The Stakeholder Communications agent manages the relationship between a project or programme and the people who have a stake in its outcome. It plans communications, drafts messages, coordinates delivery across multiple channels, tracks whether stakeholders are engaged, collects feedback, and ensures that the right people receive the right information at the right time.

Communication failure is one of the most frequently cited causes of project difficulty — stakeholders who feel uninformed, executives who are surprised by bad news, teams who lack the context they need to support delivery. This agent systematises communication so that it is consistent, timely, and appropriate to each audience.

---

## What It Does

**It maintains a stakeholder register.** The agent holds a structured register of all stakeholders for each project or programme: who they are, what their interest and influence levels are, how they prefer to receive communications, what their engagement level currently is, and what their history of interaction with the project looks like. The register is used to drive all communication planning and execution.

**It classifies stakeholders.** Using an influence/interest matrix, the agent classifies each stakeholder into a quadrant — high influence/high interest (key players to be managed closely), high influence/low interest (to be kept satisfied), low influence/high interest (to be kept informed), low influence/low interest (to be monitored). This classification drives the communication frequency, depth, and channel appropriate for each stakeholder.

**It creates communication plans.** Based on the stakeholder register and the project's communication requirements, the agent creates a communication plan that specifies what communications will be sent, to whom, through which channel, at what frequency, and for what purpose. The plan covers routine communications — weekly status reports, monthly portfolio updates — as well as event-driven communications — gate decisions, risk escalations, significant schedule changes.

**It drafts and personalises messages.** When a communication is due, the agent drafts it using the platform's LLM, drawing on current project data — status, health score, key milestones, recent decisions — to produce accurate, timely content. Messages are personalised to the recipient: an executive receives a high-level strategic summary; a project manager receives a detailed operational update; a workstream lead receives information specific to their area. Personalisation also covers tone, language, and level of technical detail.

**It delivers across multiple channels.** Messages are delivered through whichever channel each stakeholder prefers — email, Microsoft Teams, Slack, SMS, push notification, or the platform's notification centre. Consent is enforced: the agent only delivers to channels for which consent has been recorded. For stakeholders who receive high volumes of messages, digest batching consolidates multiple notifications into a single, organised summary.

**It supports multiple languages.** Notification templates are available in multiple languages. Messages are generated in the recipient's preferred language where configured, ensuring that international stakeholders receive communications in a language they can engage with easily.

**It schedules events and meetings.** The agent can schedule project meetings, review sessions, and governance events — creating calendar invitations through Microsoft Calendar integration and tracking attendance. It can also generate meeting agendas based on the current project status and the topics relevant to each meeting type.

**It collects feedback and tracks sentiment.** Following communications, the agent can collect structured feedback from stakeholders and analyse the sentiment of any informal comments or responses received. Sentiment tracking provides an ongoing indicator of stakeholder mood — identifying stakeholders who are becoming disengaged or concerned before those feelings become a project risk.

**It tracks engagement metrics.** The agent monitors engagement with each communication — whether emails are opened, whether meeting invitations are accepted, whether feedback is provided — and produces an engagement health score for each stakeholder. Low engagement triggers a prompt to review the communication approach for that individual.

**It synchronises with CRM systems.** For organisations that manage stakeholder relationships through Salesforce or other CRM platforms, the agent synchronises stakeholder profiles and communication history, ensuring consistency between the project communications record and the enterprise relationship management system.

---

## How It Works

The agent uses the platform's LLM gateway to generate message content from project data inputs. Template localisation ensures that messages are formatted correctly for each recipient's preferred language. Delivery is managed through the notification service, which handles routing to email, Teams, Slack, and other channels. Communication history is persisted to a database store that maintains the full record of every interaction with every stakeholder.

A test suite verifies channel resolution logic, digest queue behaviour, template localisation, and delivery metrics tracking.

---

## What It Uses

- Stakeholder register from Agent 08 — Project Definition and Scope (initial population)
- Current project status data from multiple agents for message content
- The platform's LLM gateway for message drafting and personalisation
- Localised communication templates (English, French, and extensible to other languages)
- Email, Microsoft Teams, Slack, SMS, and push notification channels
- Microsoft Calendar integration for event scheduling
- Sentiment analysis for feedback processing
- Salesforce CRM integration for stakeholder profile synchronisation
- Agent 03 — Approval Workflow for communications that require sign-off before sending
- The notification service for outbound message delivery

---

## What It Produces

- **Stakeholder register**: classified, profiled record of all project stakeholders
- **Communication plan**: scheduled calendar of all planned project communications
- **Drafted messages**: LLM-generated, data-driven, personalised communications
- **Multi-channel delivery records**: confirmation of message delivery with timestamp and channel
- **Engagement metrics**: open rates, response rates, and engagement health scores per stakeholder
- **Sentiment analysis results**: mood indicators derived from stakeholder feedback and responses
- **Meeting schedules and agendas**: calendar invitations with structured agenda items
- **Communication history**: complete log of every interaction with every stakeholder
- **Digest notifications**: consolidated summary messages for high-volume recipients

---

## How It Appears in the Platform

The **Notification Centre** page in the platform provides a consolidated view of all outbound communications — what was sent, to whom, when, and through which channel. Stakeholders can view their own notification preferences and communication history.

The stakeholder register and communication plan are accessible from the Communications stage in the **Methodology Map** and are presented in the **Spreadsheet Canvas** for detailed management. The engagement metrics dashboard — showing stakeholder engagement levels and sentiment trends — is available in the **Dashboard Canvas**.

The assistant panel can generate communications on request: "Draft a status update for the executive steering committee" or "Send a milestone alert to the project sponsors" — producing a draft message that can be reviewed before sending.

---

## The Value It Adds

Poor stakeholder communication is a perennial project risk. The Stakeholder Communications agent ensures that communication is planned, consistent, personalised, and measured — rather than ad hoc, inconsistent, and unmeasured. For complex programmes with dozens of stakeholders across multiple organisations, this level of communication management would require dedicated resource without the agent.

The sentiment tracking and engagement metrics provide an early warning system for stakeholder problems. A disengaged executive or a stakeholder whose messages are consistently being ignored is a risk to project success. The agent makes these signals visible before they become crises.

---

## How It Connects to Other Agents

The Stakeholder Communications agent draws content from project data across the platform — health scores from **Agent 09**, financial data from **Agent 12**, risk updates from **Agent 15**, milestone data from **Agent 10**. It uses the knowledge base from **Agent 19** for context. Formal communications requiring approval are routed through **Agent 03 — Approval Workflow**. Engagement and sentiment data feeds into **Agent 22 — Analytics and Insights** for stakeholder health reporting.
