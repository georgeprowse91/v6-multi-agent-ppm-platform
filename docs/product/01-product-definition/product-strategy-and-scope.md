# Product Strategy and Scope

**Purpose:** Single canonical statement of what the platform is, why it exists, what problems it solves, and what value it delivers. All other documents link here for the problem statement, value proposition, and differentiators rather than repeating them.

**Audience:** Executive sponsors, product owners, sales leads, new team members.

**Owner:** Product Management

**Last reviewed:** 2026-03-01

**Related docs:**
- [Requirements Specification](requirements-specification.md) — Functional and non-functional requirements
- [Market and Problem Analysis](../02-commercial/market-and-problem-analysis.md) — Market context and research data
- [Solution Index](../../solution-index.md) — Cross-cutting implementation index

---

## The Problem We Are Solving

Every large organisation runs dozens — sometimes hundreds — of projects simultaneously. The teams responsible for governing those projects, programmes and portfolios spend most of their time doing the wrong things: copy-pasting data between spreadsheets and systems, chasing status updates by email, re-creating documents that already exist in another tool, and manually enforcing governance processes that are only written down somewhere in a SharePoint folder nobody visits.

The result is predictable. Projects run over budget. Milestones slip. Governance is applied inconsistently. Executives lack the real-time visibility they need to make good investment decisions. And delivery teams feel buried under administrative work that gets in the way of actually delivering.

This is not a people problem. It is a tooling and process problem. The tools organisations use were not designed to work together, and none of them were designed to think.

---

## What the Platform Is

The **Multi-Agent PPM Platform** is an AI-native project portfolio management workspace. It gives organisations a single, intelligent environment in which to manage the full lifecycle of every project, programme and portfolio — from initial idea through to benefits realisation and lessons learned.

The platform does not replace the specialist tools your organisation already uses. Jira still tracks your development work. SAP still holds your financial data. Planview or Clarity still manages your resource capacity. What the platform does is sit above all of those systems and act as the thinking layer: it reads and writes to your tools, interprets your intent in natural language, enforces your governance processes, automates your routine work, and surfaces the right information at the right time to the right person.

At its heart, the platform is built around three ideas:

1. **Your methodology is your navigation.** Rather than giving users a generic menu of features, the platform turns your chosen project delivery approach — whether that is predictive waterfall, agile adaptive, or a hybrid of the two — into the actual navigation structure of the application. You always know where you are in the lifecycle, what you need to complete before moving forward, and what the platform expects of you.

2. **AI is the primary interface.** Users do not have to learn complex menus or know which agent to invoke. They simply describe what they need in plain English, and an orchestration layer routes that request to the right combination of specialist agents, assembles a coherent response, and presents it in the workspace.

3. **Agents are the workforce.** Behind the natural language interface is a network of 25 specialised AI agents, each responsible for a specific domain of project and portfolio management. They collaborate automatically, take direction from users, and can act autonomously on routine tasks — freeing delivery teams to focus on work that requires human judgement. For full agent specifications, see the [Agent Catalog](../../agents/).

---

## Product Scope

### In Scope

The platform covers the full project and portfolio lifecycle:

- **Demand and intake** — capturing, classifying, and routing project requests from any channel.
- **Business case and investment** — generating business cases, modelling ROI, supporting funding decisions.
- **Portfolio strategy and optimisation** — prioritising investments, capacity-constrained portfolio selection, scenario modelling.
- **Programme management** — grouping related projects, managing cross-project dependencies, tracking benefits.
- **Project delivery** — charter generation, scope management, scheduling, resource management, financial tracking, vendor procurement, quality assurance, risk and issue management, compliance, change management, release management, and knowledge management.
- **Platform operations** — workflow automation, analytics and reporting, data synchronisation, system health monitoring.
- **Governance** — stage-gate enforcement, approval workflows, audit logging, RBAC.
- **Connectors** — bi-directional integration with 44 enterprise systems (17 production-ready, 27 in development) across PPM, ERP, HRIS, collaboration, and GRC categories. For the full connector catalog, see [Connector Documentation](../../connectors/).

### Out of Scope

- Development of custom hardware or proprietary IoT devices beyond the platform's standard IoT connector.
- Changes to source-of-record systems (Planview, Jira, SAP, etc.) that the connectors integrate with.
- Custom ERP or HRIS configuration in client environments.

---

## Implementation Alignment

The repository contains a working implementation of the core execution stack: API gateway, orchestration service, workflow service, agent runtime, 14 FastAPI Python microservices, a React 18 web console with methodology navigation and assistant panel, and a React Native mobile application. The platform runs on PostgreSQL 15 and Redis 7, with Azure OpenAI providing LLM capabilities via LangChain.

For architecture details, see the [Architecture Documentation](../../architecture/). For the cross-cutting solution index, see [docs/solution-index.md](../../solution-index.md). Validate any feature claims in commercial collateral against these references before using them in delivery commitments.

---

## Core Value Proposition

### For Delivery Teams

Delivery teams spend less time on administrative work and more time on actual delivery. The platform's agents draft the documents, track the risks, reconcile the budgets and send the status updates that used to consume project managers' days. The methodology map makes clear what is expected at each stage. The AI assistant provides guidance on demand. The result is faster, more consistent delivery with less rework.

### For Portfolio Leaders

Portfolio leaders gain real-time visibility across all initiatives without having to chase status reports. They can see which projects need intervention, where the portfolio is over-committed on resources, and whether the portfolio as a whole is aligned with organisational strategy. Scenario modelling allows them to evaluate trade-offs and communicate investment decisions with confidence.

### For Executives

Executives see a portfolio health dashboard that gives them a clear, current, data-driven picture of the organisation's project investments. They can drill down into any initiative, see the latest financial performance, and understand the risk profile — without needing to attend every steering committee or read every status report.

### For the Organisation

At the organisational level, the platform creates a shared standard for how projects are delivered. Best practices are embedded in the methodology map. Governance is consistently enforced. Lessons learned are captured and made accessible. Over time, the platform's continuous improvement agents help the organisation become genuinely better at delivery — not just more efficient at managing the same problems.

---

## Unique Differentiators

**Methodology as Navigation:** Unlike generic PPM tools that rely on static menus, this platform turns the methodology itself into the navigation mechanism. Users always know what step they are on and what deliverables are required. See [User Journeys and Stage Gates](user-journeys-and-stage-gates.md) for the operational detail.

**AI-Native Architecture:** The AI assistant is not a bolt-on; it is the primary interface. Agents use large language models and machine-learning algorithms to interpret intent, generate content, optimise portfolios and predict outcomes. See [AI Architecture](../../architecture/ai-architecture.md) for technical depth.

**Modular Agents and Connector Marketplace:** Organisations can enable only the agents they need and connect to their existing tools. New agents can be added to support emerging use cases without rewriting core code. See the [Agent Catalog](../../agents/) and [Connector Documentation](../../connectors/).

**Embedded Governance and Compliance:** The platform embeds stage-gates, approval workflows, RBAC, audit trails and compliance checks into every process. It is designed to satisfy regulatory requirements such as Privacy Act 1988 (APPs), Australian ISM/PSPF and APRA CPS 234. See [Compliance Documentation](../../compliance/) for controls mapping and evidence guides.

**Continuous Improvement:** Built-in process mining and lessons-learned capture enable organisations to refine their methodologies over time and increase project success rates.

---

## Why This, Why Now

AI is transforming every knowledge-intensive profession, and project and portfolio management is no exception. The question is not whether AI will change the way organisations manage their investments and programmes — it is whether organisations will lead that change or be overtaken by it.

The Multi-Agent PPM Platform represents a considered, production-ready answer to that question. It is not a single AI feature bolted onto an existing tool. It is an architecture built from the ground up around the idea that AI agents, working together and in concert with human judgement, can transform the quality and efficiency of project delivery.

For market data and research supporting this positioning, see [Market and Problem Analysis](../02-commercial/market-and-problem-analysis.md).

---

## Document Control

| Field | Details |
|---|---|
| Owner | Product Management |
| Review cycle | Quarterly |
| Last reviewed | 2026-03-01 |
| Status | Active |
