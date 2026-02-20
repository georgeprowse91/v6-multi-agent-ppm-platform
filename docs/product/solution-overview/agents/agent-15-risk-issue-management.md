> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 15 — Risk and Issue Management

**Category:** Delivery Management
**Role:** Risk Identifier, Assessor, and Issue Tracker

---

## What This Agent Is

The Risk and Issue Management agent provides the platform's early warning system for project delivery. It helps teams systematically identify, assess and respond to risks before they become problems, and tracks issues that have already materialised to ensure they are resolved before they escalate into crises.

Risk and issue management is one of the disciplines that most distinguishes experienced project delivery from undisciplined delivery. Done well, it prevents problems. Done poorly — or not at all — it means problems are discovered late, responses are reactive, and the impact on cost, schedule, and quality is far greater than it needed to be. This agent institutionalises the discipline.

---

## What It Does

**It supports risk identification.** The agent prompts the project team to think systematically about risks using structured techniques: reviewing the project's scope, schedule, budget, resources, dependencies, and external environment for things that could go wrong. It also uses a natural language processing model — fine-tuned on risk terminology — to extract potential risks from project documents and meeting notes where they have been described informally but not formally registered.

**It assesses risks quantitatively and qualitatively.** For each identified risk, the agent supports both qualitative assessment (likelihood and impact ratings on a configurable scale) and quantitative analysis. The quantitative analysis uses an Azure ML model to predict probability and impact scores based on historical risk data from similar projects. The combined assessment places each risk in the appropriate cell of the risk matrix.

**It prioritises risks.** The agent calculates a risk exposure score for each risk — combining probability, impact, and urgency — and ranks all risks accordingly. This prioritisation guides where the project team should focus their risk response efforts. The top risks are surfaced prominently in the risk dashboard.

**It runs Monte Carlo simulation for quantitative schedule and cost risk.** For projects where quantitative risk analysis is required, the agent can run Monte Carlo simulations that model the combined effect of all identified risks on the project's schedule and budget. The output is a probability distribution of project outcomes — showing, for example, the probability of completing within budget or the range of likely completion dates — rather than a single optimistic plan.

**It creates and tracks mitigation plans.** For each risk that warrants a response, the agent helps define a mitigation plan: the actions that will be taken to reduce the probability or impact of the risk, who is responsible, and when the actions should be completed. These actions are tracked as tasks within the platform, ensuring that risk responses actually happen rather than being defined and then forgotten.

**It monitors risk triggers.** Many risks have early warning indicators — precursor events that suggest the risk is becoming more likely. The agent monitors configured trigger conditions and raises an alert when a trigger event is detected, prompting the team to review the risk response before the risk fully materialises.

**It manages the issue log.** When a risk materialises — or when a new problem arises that was not previously identified as a risk — it is logged as an issue. The agent tracks issues through their resolution lifecycle: identified, assigned, in progress, resolved. It applies escalation rules to ensure that unresolved issues are escalated to the appropriate level of management before they breach their resolution deadline.

**It generates a risk matrix and dashboard.** The risk matrix provides a visual heat map of the project's risk exposure — plotting each risk by likelihood and impact to give an immediate visual representation of the risk profile. The risk dashboard summarises the top risks, their current status, and the overall risk exposure trend.

**It integrates with GRC systems.** For organisations that manage enterprise risk through ServiceNow or RSA Archer, the agent synchronises project risk data with these systems — ensuring that project-level risks are visible in the enterprise risk picture and that the project benefits from any enterprise-level risk intelligence.

---

## How It Works

The agent uses a BERT-based natural language model, fine-tuned on risk language, to extract potential risks from unstructured project text. The Azure ML model provides probability and impact predictions calibrated against historical project risk data. Monte Carlo simulation applies statistical sampling to model the combined schedule and cost impact of the risk portfolio. The agent stores the risk register in the platform's database and synchronises it with connected GRC and project management tools.

---

## What It Uses

- Project scope, schedule, and budget data from Agents 08, 10, and 12
- A fine-tuned BERT model for risk extraction from project documents
- Azure ML for risk probability and impact prediction
- Azure Cognitive Search for accessing a knowledge base of mitigation guidance
- Monte Carlo simulation engine for quantitative risk analysis
- GRC system integrations: ServiceNow, RSA Archer
- PM tool integrations: Planview, Microsoft Project, Jira, Azure DevOps
- Agent 03 — Approval Workflow for escalation decisions
- Agent 09 — Lifecycle and Governance as a consumer of risk status data
- Azure Synapse and Data Lake for risk dataset storage

---

## What It Produces

- **Risk register**: a structured record of all identified risks with probability, impact, priority, owner, and response plan
- **Risk matrix**: a heat map visualisation of risk exposure across the project
- **Risk prioritisation**: ranked list of risks by exposure score
- **Monte Carlo simulation results**: probability distribution of schedule and cost outcomes
- **Mitigation plans**: defined actions, owners, and timelines for each prioritised risk response
- **Trigger monitoring alerts**: notifications when risk trigger conditions are detected
- **Issue log**: tracked issues with status, owner, and resolution timeline
- **Risk dashboard**: top risks, exposure trend, and overall risk health indicator
- **Risk report**: structured narrative report suitable for governance review

---

## How It Appears in the Platform

The risk register is accessible from the risk management stage in the **Methodology Map** navigation, and the content is presented in the **Spreadsheet Canvas** where individual risks can be reviewed, updated, and filtered. The risk matrix heat map is displayed in the **Dashboard Canvas**, with colour coding indicating the concentration of risk in each likelihood/impact zone.

The risk dashboard — top risks, exposure trend, open issues — is available both in the project dashboard and as a summary in the portfolio-level dashboard managed by Agent 22. The assistant panel supports risk queries: "What are our top five risks?" "Are there any escalated issues?" "What is our current risk exposure trend?"

---

## The Value It Adds

Projects that manage risk proactively experience significantly better outcomes than those that manage it reactively. The Risk and Issue Management agent provides the structure, the prompts, and the tooling to make systematic risk management achievable without requiring the project team to have deep specialist expertise in risk methodology.

The quantitative analysis capabilities — ML-based probability estimation and Monte Carlo simulation — go well beyond what most project teams can do with a spreadsheet, providing an evidence-based, statistically grounded view of project risk exposure that supports better-informed decisions at both the project and portfolio level.

---

## How It Connects to Other Agents

The Risk and Issue Management agent draws on scope, schedule, and financial data from **Agents 08, 10, and 12**. Risk status feeds into **Agent 09 — Lifecycle and Governance** for project health scoring and stage-gate assessments. The risk portfolio feeds into **Agent 22 — Analytics and Insights** for portfolio risk reporting. Risk-related compliance implications are surfaced to **Agent 16 — Compliance and Regulatory**. Budget risk data connects to **Agent 12 — Financial Management**.
