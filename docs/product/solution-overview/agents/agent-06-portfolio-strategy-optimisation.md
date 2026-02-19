# Agent 06 — Portfolio Strategy and Optimisation

**Category:** Portfolio Management
**Role:** Investment Prioritisation and Portfolio Advisor

---

## What This Agent Is

The Portfolio Strategy and Optimisation agent is the strategic brain of the platform at the portfolio level. It looks across all active and proposed projects simultaneously — weighing their strategic value, their costs, their risks, their resource demands, and the organisation's capacity constraints — and produces a prioritised, optimised view of the portfolio that tells decision-makers where to invest, where to hold, and where to stop.

This is the agent that answers the hardest questions in portfolio management: "Given everything on our plate and everything in our pipeline, what should we focus on?" It replaces intuition-led portfolio reviews with evidence-based, multi-criteria analysis.

---

## What It Does

**It scores and ranks projects across multiple dimensions.** The agent evaluates every project and proposal in the portfolio against a consistent set of criteria: strategic alignment with the organisation's objectives, expected return on investment, risk level, urgency, dependency on other initiatives, and resource intensity. Each dimension is weighted according to the organisation's configured priorities, and every project receives a composite score that reflects its overall value relative to others in the portfolio.

**It performs capacity-constrained optimisation.** Scoring projects is only half the challenge. The other half is working out which combination of projects the organisation can actually deliver given its available budget, people, and time. The agent applies optimisation algorithms to find the portfolio mix that maximises total strategic value subject to the actual constraints in play. It does not just recommend what is most valuable in isolation — it recommends what is most valuable given what is realistically achievable.

**It supports multiple optimisation approaches.** Depending on the complexity of the portfolio and the preferences of the investment committee, the agent can apply different approaches: integer programming for mathematically optimal solutions under strict constraints, mean-variance analysis for balancing return against risk, the Analytic Hierarchy Process for structured multi-criteria comparison, or multi-objective optimisation for scenarios where trade-offs between competing priorities need to be explicitly surfaced.

**It runs what-if scenario analysis.** The agent allows portfolio managers and executives to model the impact of portfolio changes before they are made. What happens to total portfolio value if this programme is deferred by a quarter? What if the budget is cut by fifteen percent — which projects should be deprioritised? What if a new strategic priority emerges — how should the portfolio be rebalanced? Each scenario is modelled quickly, and the results are presented as a comparison against the current portfolio state.

**It evaluates policy guardrails.** Portfolio decisions are not made in a vacuum. The agent checks proposed portfolio configurations against the organisation's investment policies — minimum diversification requirements, maximum concentration in any single domain, mandatory compliance investments that cannot be deferred — and flags any configuration that would breach these guardrails.

**It produces rebalancing recommendations.** When the portfolio has drifted from its optimal configuration — because new priorities have emerged, projects have been delayed, or resource capacity has changed — the agent analyses the gap and produces a set of specific rebalancing actions: projects to accelerate, projects to pause, proposals to promote into delivery, and initiatives to close.

---

## How It Works

The agent ingests the scored outputs of individual business cases from Agent 05, the resource capacity picture from Agent 11, and the current portfolio status from the platform's data store. It applies its optimisation algorithms to this combined dataset and produces both a portfolio health assessment and a set of recommendations.

The agent's scoring model is configurable per tenant: the weight given to strategic alignment versus financial return versus risk versus urgency can be adjusted to match the organisation's current priorities. This means the same platform can serve an organisation that prioritises financial return above all else and one that prioritises regulatory compliance, without requiring any code changes.

All recommendations are versioned and auditable — the agent records the inputs, the scoring weights, the algorithm used, and the resulting recommendation for every optimisation run, so that the basis for portfolio decisions can be reviewed and challenged at any point.

---

## What It Uses

- Business case data and financial metrics from Agent 05
- Resource capacity and constraint data from Agent 11
- Current portfolio status from the platform's data store
- Configurable scoring weights and strategic objective definitions
- Multiple optimisation algorithms: integer programming, mean-variance, AHP, multi-objective
- Policy guardrail definitions
- Agent 03 — Approval Workflow for routing portfolio recommendations for executive sign-off
- The platform's event bus for publishing portfolio change events

---

## What It Produces

- A **scored and ranked portfolio view** showing every active and proposed project with its composite strategic value score
- A **capacity-constrained optimised portfolio**: the recommended portfolio given actual resource and budget constraints
- **What-if scenario results**: modelled comparisons of alternative portfolio configurations
- **Policy guardrail assessments**: flags for any configurations that would breach investment policies
- **Rebalancing recommendations**: specific, actionable changes to bring the portfolio back into alignment with strategic priorities
- **Portfolio health summary** showing overall alignment, resource utilisation, and risk distribution

---

## How It Appears in the Platform

The portfolio-level **Dashboard Canvas** presents the optimised portfolio as a visual scorecard — each project shown with its strategic alignment score, financial value, risk level, and status. The colour coding makes it immediately clear which projects are performing well, which are at risk, and which are misaligned with the current strategy.

The scenario modelling capability is accessible through the assistant panel: a portfolio manager can ask the platform to model a specific change — "what happens if we defer Project X?" — and receive a before-and-after comparison directly in the canvas. Formal portfolio reviews and rebalancing decisions are routed through the Approvals workflow so that they are properly governed and recorded.

---

## The Value It Adds

Most organisations make portfolio investment decisions through a combination of gut feeling, political influence, and a spreadsheet that somebody spent three weeks building. The output is a portfolio that reflects who argued most persuasively in the last investment committee meeting, not what actually creates the most value.

The Portfolio Strategy and Optimisation agent replaces that process with evidence-based multi-criteria analysis that is transparent, consistent, and auditable. Every project is evaluated on the same criteria. The constraints are real. The scenarios are modelled, not guessed. And the basis for every recommendation is recorded, so that when the investment committee is challenged on a decision six months later, the reasoning is available.

---

## How It Connects to Other Agents

The Portfolio Strategy and Optimisation agent draws on business case data from **Agent 05** and resource capacity data from **Agent 11**. Its outputs inform the programme structure that **Agent 07 — Programme Management** creates and the financial baselines that **Agent 12 — Financial Management** tracks. Portfolio decisions approved through this agent are surfaced in the analytics dashboards managed by **Agent 22 — Analytics and Insights**.
