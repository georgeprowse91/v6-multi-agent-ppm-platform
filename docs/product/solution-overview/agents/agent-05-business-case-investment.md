# Agent 05 — Business Case and Investment Analysis

**Category:** Portfolio Management
**Role:** Financial Justification and Investment Advisor

---

## What This Agent Is

The Business Case and Investment Analysis agent turns a project idea into a structured investment proposition. It takes the information captured during demand intake and builds out a complete financial and strategic analysis — including cost modelling, benefit quantification, return on investment calculations, scenario comparisons, and a recommendation on whether to proceed.

This is the agent that makes the case for or against investing in a project. It does the analytical heavy lifting that project teams and finance functions would otherwise spend days or weeks doing manually — producing a document-ready business case with rigorous financial modelling in a fraction of the time.

---

## What It Does

**It generates business cases from structured templates.** The agent uses the platform's business case template library — tailored to different project types such as capital investment, technology delivery, regulatory compliance, or operational improvement — to produce a properly structured document. The template ensures that every business case contains the sections expected by the organisation's governance process: strategic alignment, problem statement, options analysis, cost-benefit analysis, risk summary, and recommendation.

**It performs cost-benefit analysis.** The agent models the expected costs of the initiative across its full lifecycle — capital costs, implementation costs, ongoing operational costs, and decommissioning costs — and quantifies the expected benefits: efficiency savings, revenue generation, risk reduction, regulatory compliance value, or strategic positioning gains. It calculates the net benefit and presents a clear picture of whether the investment is financially justified.

**It calculates key financial metrics.** For each business case, the agent calculates Net Present Value (NPV), Internal Rate of Return (IRR), payback period, and Total Cost of Ownership (TCO). These metrics are calculated using configurable discount rates and inflation assumptions, and support multi-currency scenarios for organisations operating across multiple markets.

**It models scenarios and sensitivity.** Rather than presenting a single set of numbers, the agent models multiple scenarios — a base case, an optimistic case, and a conservative case — showing how the financial outcome changes under different assumptions. It also runs sensitivity analysis, identifying which assumptions have the greatest impact on the result and presenting the range of outcomes if those assumptions prove incorrect.

**It runs Monte Carlo simulation.** For more complex investment decisions, the agent can run probabilistic simulations — testing the business case against thousands of randomly sampled combinations of cost and benefit assumptions — to produce a probability distribution of outcomes rather than a single point estimate. This gives decision-makers a realistic sense of the uncertainty in the numbers rather than a false precision.

**It benchmarks against historical projects.** The agent compares the proposed investment against a library of historical projects to assess whether the cost and benefit estimates are realistic, whether similar initiatives have delivered as expected, and what lessons from past experience should inform the current decision.

**It produces an investment recommendation.** Drawing on the financial analysis, the scenario modelling, the risk assessment and the historical comparison, the agent produces a clear recommendation — proceed, do not proceed, or proceed with conditions — along with the confidence level of that recommendation and the key factors driving it.

---

## How It Works

The agent draws on the enriched demand record produced by Agent 04 as its starting point. It uses the platform's LLM gateway to generate narrative sections of the business case from structured data inputs, and applies financial calculation libraries to produce the quantitative analysis. Where external market data is available — such as benchmark costs for a particular type of technology project — the agent can retrieve and incorporate that information to ground the estimates in real-world comparisons.

The generated business case is stored in the platform's document canvas as a versioned document, allowing it to be reviewed, commented on, and revised through the platform's document editing workflow. Changes to assumptions trigger a recalculation of the financial metrics so that the document always reflects the most current analysis.

---

## What It Uses

- The demand record from Agent 04 as the starting input
- Business case document templates from the platform's template library
- Financial calculation logic for NPV, IRR, payback period, TCO and multi-currency conversion
- Monte Carlo simulation for probabilistic analysis
- Sensitivity analysis across configurable assumption dimensions
- A library of historical project data for benchmarking
- External market data for grounding cost and benefit estimates
- The platform's LLM gateway for narrative generation
- The document canvas for storing and presenting the business case
- Agent 03 — Approval Workflow for routing the completed business case for sign-off

---

## What It Produces

- A **complete business case document** stored in the document canvas, structured according to the organisation's template and containing all required sections
- **Financial metrics**: NPV, IRR, payback period, TCO for each scenario
- **Scenario comparisons**: base, optimistic and conservative cases side by side
- **Sensitivity analysis**: identification of the key assumptions and their range of impact
- **Monte Carlo results**: probability distribution of outcomes for complex investments
- **Investment recommendation** with confidence level and supporting rationale
- **Benchmark comparison** against historical similar projects

---

## How It Appears in the Platform

When a business case is generated, it appears in the **Document Canvas** of the relevant project workspace, pre-populated with all the sections the platform's template defines. The financial metrics are presented in formatted tables, and the scenario analysis is shown as a comparison view that allows reviewers to see the optimistic, base and conservative cases side by side.

The business case document can be edited directly within the document canvas. As assumptions are changed, the financial metrics update automatically. Comments and review notes can be added inline, and the document passes through the Approvals workflow before it is formally signed off.

On the portfolio analytics dashboard, approved business cases contribute their NPV and strategic alignment scores to the portfolio-level investment view.

---

## The Value It Adds

Building a rigorous business case is time-consuming work that requires financial skills, structured thinking, and access to historical data that most project teams do not have readily at hand. The Business Case and Investment Analysis agent compresses this work from days to minutes, produces a consistently structured output that meets governance standards, and applies analytical rigour — Monte Carlo simulation, sensitivity analysis, historical benchmarking — that goes beyond what most organisations manage in practice.

For investment committees and portfolio boards, the consistency of the output means that every business case they review is structured the same way, uses the same financial methodology, and can be compared directly against others in the portfolio — making investment decisions significantly easier and more defensible.

---

## How It Connects to Other Agents

The Business Case and Investment Analysis agent receives its input from **Agent 04 — Demand and Intake** and routes completed business cases to **Agent 03 — Approval Workflow** for sign-off. Approved business cases feed into **Agent 06 — Portfolio Strategy and Optimisation**, which uses the financial metrics and strategic alignment scores to rank and prioritise the portfolio. The financial baseline established in the business case also forms the starting point for **Agent 12 — Financial Management** once the project is approved and enters delivery.
