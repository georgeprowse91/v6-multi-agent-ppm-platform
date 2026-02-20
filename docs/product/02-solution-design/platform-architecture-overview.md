# Platform Architecture Overview

**Purpose:** Describe the technical architecture, deployment concepts, connector platform model, and core system design of the Multi-Agent PPM Platform.
**Audience:** Solution architects, engineering leads, integration engineers, and technical reviewers.
**Owner:** Architecture Lead
**Last reviewed:** 2026-02-20
**Related docs:** [../01-product-definition/product-strategy-and-scope.md](../01-product-definition/product-strategy-and-scope.md) · [agent-system-design.md](agent-system-design.md) · [connectors/iot-connector-spec.md](connectors/iot-connector-spec.md)

> **Migration note:** Consolidated from `solution-overview/platform-overview.md` on 2026-02-20. Architecture-related excerpts previously in `solution-overview/pitch-overview.md` are now referenced from this document.

---

# Platform Overview

## Introduction

The Multi‑Agent PPM Platform is an AI‑powered Project Portfolio Management (PPM) workspace built for modern enterprises. It combines the rigour of methodology‑driven navigation with the flexibility of an interactive canvas and the power of specialised AI agents. Rather than yet another standalone tool, it orchestrates your existing systems of record—Planview, Jira, SAP, Workday and more—through an AI assistant that guides users along pre‑defined project methodologies and automates routine work. This overview distills the core concepts, capabilities and value proposition of the solution as outlined in the architecture document.

## Implementation alignment

This overview maps to the current repository implementation. The repo provides a working API gateway, orchestration service, workflow engine, agent runtime and configuration, connector registry, data sync service, analytics service, data-lineage service, and a web console (`apps/web`). The web console ships with methodology navigation, a workspace canvas with document/timeline/dashboard tabs, an assistant panel, and a connector gallery backed by the connector hub. The connector gallery supports instance lifecycle and health updates, while credentials and sync scheduling remain managed through configuration and secrets.

## Core Concepts

### Methodology‑Driven Navigation

**At the heart of the platform is a methodology map:** a visual workflow that guides users through the entire project lifecycle. Whether your organisation follows Predictive, Adaptive, or a hybrid approach, the platform turns the methodology into the primary navigation mechanism. Each stage (e.g., Initiation, Planning, Execution, Monitoring and Closing) contains detailed sub‑tasks and stage‑gates that must be completed. The left panel of the user interface displays this map, allowing users to see where they are and what comes next. Selecting a node surfaces the relevant tasks and documentation, ensuring consistent governance and best practice across projects.

### AI as the Primary Interface

Instead of forcing users to navigate multiple applications, the platform provides a conversational assistant. This assistant understands natural language commands and generates rich responses by orchestrating multiple agents behind the scenes. For example, a user might ask: “Create a new project for a software rollout and generate a charter.” The assistant routes the request to the appropriate agents, summarises the information, and presents the results in the central canvas. The AI also provides proactive guidance, reminding users of upcoming stage‑gates and recommending next best actions. The architecture document emphasises that the AI becomes the primary interface for project managers, removing the need to manually interact with Planview or Jira.

### Agents as the Workforce

The platform uses a network of specialised agents to handle each domain process—demand intake, business case generation, portfolio optimisation, program management, scheduling, resource management, financial management, vendor procurement, quality assurance, risk management, compliance, and more. Each agent encapsulates the logic, rules and integrations required to perform its function. Agents collaborate via an orchestration layer: the Intent Router determines the user’s intent, Response Orchestration sequences calls to downstream agents, and domain agents read/write data from systems of record. This modular architecture allows new capabilities to be introduced or replaced without disrupting the whole system.

### Interactive Canvas

The central canvas is the workspace where content and data from multiple sources are assembled. The current web console provides a three‑panel layout: a methodology map on the left, a tabbed workspace canvas in the center, and an assistant/context panel on the right. Canvas tabs include Documents (create and classify project artefacts), Timeline (track milestones and export schedules), and Dashboard (portfolio health KPIs sourced from the analytics service). These panels provide a “single pane of glass” while keeping source‑of‑truth updates flowing through connectors and agent workflows.

### Connector Marketplace

**Integration is not an afterthought:** the platform includes a connector registry and connector hub that power the web console’s connector gallery. Each connector encapsulates authentication, data mapping and error handling for an external system, and exposes consistent APIs to agents and workflows. Operators can enable or disable connector instances and track health status in the gallery, while auth secrets and sync schedules are managed through `config/connectors/integrations.yaml` and environment-specific secret stores.

## Key Capabilities

The platform offers a broad set of capabilities spanning the entire project and portfolio lifecycle. Some highlights include:

**Demand Management:** Capture and triage ideas and project requests via forms, Slack, email or Teams. Perform duplicate detection, classify requests by type and complexity, and route them for review.

**Business Case & Investment Analysis:** Generate detailed business cases automatically, perform cost–benefit analysis and ROI modelling using scenario simulations, and recommend whether to proceed.

**Portfolio Strategy & Optimisation:** Apply multi‑criteria decision analysis and capacity‑constrained optimisation to prioritise projects based on strategic alignment, benefits, risk and resource availability. Explore what‑if scenarios to rebalance the portfolio as conditions change.

**Program & Project Management:** Define programs, group related projects, manage dependencies and benefits, and generate program roadmaps. Create project charters, scope baselines and Work Breakdown Structures (WBS). Manage lifecycle stages, enforce gates, monitor health scores, track schedules and tasks, allocate resources, track budgets, handle vendor procurement, and manage quality, risks and issues.

**Compliance & Governance:** Apply methodology‑specific stage‑gates and ensure that required artefacts (charters, cost approvals, risk assessments, QA reviews) are completed before advancing. Implement RBAC and field‑level security to restrict who can view or edit data.

**Analytics & Insights:** Provide dashboards and reports on portfolio health, program benefits, project costs, risk exposure, resource utilisation, vendor performance and more. Use predictive models to forecast schedule delays, cost overruns or risk events.

**Continuous Improvement:** Capture lessons learned and retro insights, perform process mining to identify bottlenecks, and update templates and methodologies. Provide an AI library of best practices and suggestions.

## Use‑Case Scenarios

### Predictive Example

Consider a capital infrastructure project. A new demand comes in from a business unit. The Demand & Intake agent captures the request and classifies it as a “capital project.” The Business Case agent generates a cost–benefit analysis, which is approved via the Approval Workflow agent. The Portfolio Strategy agent evaluates the business case against existing portfolio constraints and recommends adding it. The Program Management agent creates a program if related initiatives exist. The Project Definition agent generates a charter and detailed scope, while the Schedule & Planning agent converts the WBS into a baseline schedule. As the project moves through phases (Initiation → Planning → Execution → Monitoring → Closing) represented in the methodology map, the Project Lifecycle & Governance agent enforces stage‑gates (e.g., requiring a signed charter before leaving Initiation). Resource & Capacity, Financial Management, Vendor Procurement, Quality, Risk and Compliance agents perform their roles, while the Knowledge Management agent captures documentation. Reporting & Insights summarises progress, and Continuous Improvement agents feed lessons back into templates.

### Adaptive Example

For an Adaptive software project, the methodology map shows Sprints rather than phases. During a Sprint, the Schedule & Planning agent handles backlog refinement and sprint planning, while the Resource agent ensures capacity. The Portfolio Strategy agent may re‑prioritise backlog items based on strategic value. Daily stand‑up summaries and risk alerts appear in the canvas via the Communications agent. The methodology map resets for each Sprint (Planning → Execution → Review → Retrospective). The agents still orchestrate tasks—requests, approvals, budget updates, vendor onboarding, code review quality checks, compliance scans and release planning—but in shorter cycles. The platform adapts the stage‑gates to Adaptive: instead of a single “Closing” phase, each Sprint must complete definition of done criteria before starting the next iteration.

## Value Proposition

The Multi‑Agent PPM Platform delivers several compelling benefits:

**Unified Experience:** Project managers operate from a single canvas rather than juggling multiple applications. The methodology map ensures everyone follows the same process, and the AI assistant surfaces what matters most. Data stays synchronised with source systems, reducing duplication and errors.

**Automation & Efficiency:** Specialised agents handle routine work such as generating business cases, updating schedules, creating risk registers and performing budget reconciliations. This reduces manual effort and accelerates decision‑making.

**Strategic Alignment:** Portfolio optimisation ensures investments align with organisational strategy and resource constraints. Scenario modelling helps executives understand trade‑offs and make informed decisions.

**Governance & Risk Management:** Stage‑gates enforce compliance and quality. Risk and issue management is embedded throughout the lifecycle, with proactive alerts based on predictive models.

**Interoperability & Flexibility:** The connector marketplace supports the most popular PPM, ERP and collaboration systems. Clients can mix and match tools or migrate systems without disrupting the platform. Interoperability is crucial because 87% of IT leaders consider it critical to AI adoption[1].

## Unique Differentiators

**Methodology as Navigation:** Unlike generic PPM tools that rely on static menus, this platform turns the methodology itself into the navigation mechanism. Users always know what step they are on and what deliverables are required.

**AI‑Native Architecture:** The AI assistant is not a bolt‑on; it is the primary interface. Agents use large language models and machine‑learning algorithms to interpret intent, generate content, optimise portfolios and predict outcomes.

**Modular Agents & Connector Marketplace:** Organisations can enable only the agents they need and connect to their existing tools. New agents can be added to support emerging use cases without rewriting core code.

**Embedded Governance & Compliance:** The platform embeds stage‑gates, approval workflows, RBAC, audit trails and compliance checks into every process. It is designed to satisfy regulatory requirements such as Privacy Act 1988 (APPs), Australian ISM/PSPF and APRA CPS 234.

**Continuous Improvement:** Built‑in process mining and lessons‑learned capture enable organisations to refine their methodologies over time and increase project success rates.

## Conclusion

The Multi‑Agent PPM Platform offers a comprehensive, AI‑enabled solution for managing projects, programs and portfolios. By combining methodology‑driven navigation, a conversational AI interface, a network of specialised agents and an interactive canvas that integrates with existing systems, it addresses the complexities of modern project delivery. Its modular design supports multiple methodologies, scales across industries and regions, and positions organisations to harness AI in a controlled, secure and compliant manner.

[1] 10 AI Agent Statistics for 2026: Adoption, Success Rates, & More

https://www.multimodal.dev/post/agentic-ai-statistics
