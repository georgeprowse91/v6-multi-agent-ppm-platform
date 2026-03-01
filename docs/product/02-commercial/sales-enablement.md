# Sales Enablement

**Purpose:** Messaging frameworks, pitch narratives, objection handling, and collateral index for field sales teams. This document contains only sales-specific content; for product details, agent specifications, and technical architecture, follow the links to canonical sources.
**Audience:** Account executives, sales engineers, pre-sales architects, and GTM leads.
**Owner:** Commercial Lead / Sales Enablement
**Last reviewed:** 2026-03-01
**Related docs:** [Go-to-Market Plan](go-to-market-plan.md) · [Packaging and Pricing](packaging-and-pricing.md) · [Competitive Positioning](competitive-positioning.md)

---

## Positioning Statement

The Multi-Agent PPM Platform is an AI-native orchestration layer that transforms disconnected project systems into a unified, intelligent portfolio management capability — without replacing existing investments.

For the full product narrative, value proposition, and differentiators, see [Product Strategy and Scope](../01-product-definition/product-strategy-and-scope.md).

---

## Elevator Pitches

### 30-Second Version

Large organisations waste up to 40% of PMO time on manual data aggregation across disconnected systems. Our platform sits above your existing tools — Jira, SAP, Planview, Workday — and uses 25 specialised AI agents to automate reporting, enforce governance, and surface real-time portfolio insights. No rip-and-replace. Value in weeks, not years.

### 2-Minute Version

Every enterprise we speak to has the same problem: dozens of project tools that don't talk to each other, dashboards that are weeks stale, and governance that depends on people remembering to follow the process. Our Multi-Agent PPM Platform changes this. It connects to your existing systems through 44 pre-built integrations, orchestrates 25 AI agents that each specialise in a domain of project management, and presents everything through a three-panel workspace where your methodology becomes the navigation. The AI assistant is the primary interface — users describe what they need in plain English and the platform does the rest. Stage-gates are enforced automatically. Audit trails are immutable. And portfolio leaders get real-time visibility without chasing status reports.

### 5-Minute Version

Use the 2-minute pitch above, then walk through a demo scenario using the [Demo Environment Guide](../../demo-environment.md). Show: (1) demand intake via the assistant panel, (2) automatic methodology recommendation and workspace setup, (3) the three-panel layout with methodology navigation, (4) an agent-generated risk register, and (5) the portfolio health dashboard.

---

## Messaging by Buyer Persona

| Persona | Primary Pain Point | Key Message | Proof Points |
|---|---|---|---|
| CIO / CTO | Tool sprawl and integration cost | Protect existing investments; add AI intelligence without rip-and-replace | 44 connectors, event-driven sync, open API |
| PMO Director | Manual reporting and stale dashboards | Real-time portfolio visibility and predictive support | Automated dashboards, AI health scoring, stage-gate enforcement |
| CFO / Finance | Budget overruns and poor forecasting | Better financial confidence with variance analysis and EVM | ERP integration (SAP, Oracle, NetSuite), automated forecasting |
| Project Manager | Administrative burden | Guided, compliant workflows with reduced admin load | AI-generated charters, automated risk registers, methodology map |

---

## Common Objections and Responses

| Objection | Response |
|---|---|
| "We already have a PPM tool" | The platform orchestrates your existing tools — it does not replace them. Jira, SAP, Planview, and Clarity remain your systems of record. |
| "AI isn't mature enough for enterprise PPM" | The platform uses human-in-the-loop controls with confidence scoring. Every AI recommendation can be reviewed and overridden. Audit trails track all agent actions. |
| "Integration will take too long" | Pre-built connectors for 17 production-ready systems mean initial integration can happen in weeks, not months. The connector SDK supports custom integrations. |
| "Data security concerns" | Enterprise-grade security: OIDC/Azure AD authentication, encryption at rest and in transit, RBAC/ABAC, immutable audit logs, and data residency controls. Aligned with Australian ISM/PSPF and APRA CPS 234. |
| "How is this different from Microsoft Copilot?" | Copilot is a general-purpose assistant. This platform has 25 domain-specialised agents purpose-built for PPM workflows, with methodology-embedded governance and cross-system orchestration. See [Competitive Positioning](competitive-positioning.md) for detailed battlecards. |

---

## Demo Flow Guidance

For a structured demo walkthrough, use the [Demo Environment Guide](../../demo-environment.md) and the [Demo Run Page](../../runbooks/quickstart.md).

**Recommended demo sequence:**
1. **Login and workspace setup** — Show methodology selection and connector gating
2. **Demand intake** — Submit a request via the assistant panel; show auto-classification
3. **Project workspace** — Navigate the three-panel layout; show methodology map driving navigation
4. **Agent interaction** — Ask the assistant to generate a risk register or project charter
5. **Portfolio dashboard** — Show real-time health scoring and drill-down analytics
6. **Governance** — Demonstrate stage-gate enforcement and approval workflows

---

## Collateral Index

| Collateral | Canonical Source |
|---|---|
| Product narrative and value proposition | [Product Strategy and Scope](../01-product-definition/product-strategy-and-scope.md) |
| Market data and research | [Market and Problem Analysis](market-and-problem-analysis.md) |
| Competitor battlecards | [Competitive Positioning](competitive-positioning.md) |
| Pricing and packaging | [Packaging and Pricing](packaging-and-pricing.md) |
| GTM execution plan | [Go-to-Market Plan](go-to-market-plan.md) |
| Agent capabilities (25 agents) | [Agent Catalog](../../agents/) |
| Connector ecosystem (44 integrations) | [Connector Documentation](../../connectors/) |
| Architecture and security | [Architecture Documentation](../../architecture/) |
| Compliance and regulatory | [Compliance Documentation](../../compliance/) |
| Demo environment setup | [Demo Environment Guide](../../demo-environment.md) |

---

## Messaging Guardrails

- Do not make hard numeric connector claims unless validated against the current [Connector Documentation](../../connectors/supported-systems.md).
- Position deployment options as currently documented: managed SaaS and private-cloud options are primary; other models should be presented as roadmap/strategic.
- Validate implementation-sensitive claims (SCIM, immutable audit retention semantics, exact integration breadth) against [Architecture Documentation](../../architecture/) and [Runbooks](../../runbooks/) before external use.
- All agent capability claims should reference [Agent Specifications](../../agents/agent-specifications.md) for accuracy.
