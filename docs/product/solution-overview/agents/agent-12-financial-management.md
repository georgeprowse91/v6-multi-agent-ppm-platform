# Agent 12 — Financial Management

**Category:** Delivery Management
**Role:** Budget Tracker and Financial Controller

---

## What This Agent Is

The Financial Management agent is the platform's financial intelligence layer for project and portfolio delivery. It tracks budgets, records costs, forecasts spending, analyses variances, and produces the financial reports that project managers, finance teams, and portfolio leaders need to keep investments under control.

It replaces the manual reconciliation processes that consume so much time in most project management offices — the monthly cycle of pulling actuals from the finance system, updating the spreadsheet, recalculating the forecast, and producing the report — with a continuous, automated financial monitoring capability that keeps the financial picture current at all times.

---

## What It Does

**It creates and manages budgets.** When a project is approved, the agent establishes a financial baseline from the cost estimates in the approved business case. This baseline defines the total approved budget, allocated across cost categories — labour, third-party services, licences, hardware, travel, and contingency — and distributed across the project timeline. The baseline is stored as a reference against which all subsequent financial performance is measured.

**It tracks and accrues costs.** As delivery progresses, the agent records actual costs as they are incurred — pulling transaction data from connected ERP systems (SAP, Oracle, NetSuite) and supplemented by cost entries from the project team. Accruals are applied where costs have been incurred but not yet invoiced, giving a more accurate picture of the true cost-to-date than a simple cash-basis view.

**It forecasts spending.** The agent produces an Estimate at Completion (EAC) — a forecast of the total project cost based on actual spending to date and the estimated cost of the remaining work. The forecast is recalculated whenever new actuals are received or the project scope and schedule change. Multiple forecasting methods are available, including top-down percentage adjustment, bottom-up re-estimation, and EVM-based projection.

**It analyses variances.** The agent calculates cost variance — the difference between what was planned to be spent and what has actually been spent — at every level of the project: by cost category, by work package, and at the total project level. It identifies which areas are running over or under budget, analyses the reasons for variances, and flags situations where the variance is approaching or exceeding the approved tolerance.

**It applies Earned Value Management.** For projects where EVM is required, the agent calculates the full suite of earned value metrics: Schedule Variance (SV), Cost Variance (CV), Schedule Performance Index (SPI), Cost Performance Index (CPI), and Estimate to Complete (ETC). These metrics provide an objective, integrated view of both schedule and cost performance.

**It handles multi-currency.** For projects that span multiple countries or involve international suppliers, the agent manages currency conversion, applying configurable exchange rates to produce consistent reporting in the organisation's base currency while preserving the original transaction currency for audit purposes.

**It analyses profitability.** For client-delivery organisations, the agent can track revenue alongside cost to produce profitability analysis at the project level, including ROI tracking against the business case investment commitment and IRR recalculation as actual costs emerge.

**It produces financial reports and dashboards.** The agent generates structured financial reports — cost summaries, variance analyses, forecast comparisons, EVM reports — and populates the financial sections of project and portfolio dashboards.

---

## How It Works

The agent's financial baseline is derived from the business case approved through Agent 05, adjusted for any changes approved through Agent 17 — Change and Configuration Management. Actual cost data flows in from connected ERP systems on a scheduled synchronisation cycle and through manual cost entry in the platform. The agent applies accrual logic, performs currency conversion, and recalculates all financial metrics whenever new data is received.

Budget threshold rules can be configured to trigger alerts automatically — for example, alerting the project manager when actuals reach 80% of the approved budget, or alerting the programme director when the forecast exceeds the baseline by more than 10%.

---

## What It Uses

- Approved business case cost estimates from Agent 05 as the financial baseline
- ERP system integrations: SAP, Oracle, NetSuite for actual cost data
- Workday and ADP for labour cost data
- Change records from Agent 17 for budget adjustments
- Schedule data from Agent 10 for earned value calculations
- Resource cost rate data from Agent 11
- Configurable exchange rates for multi-currency handling
- Budget threshold and alert rules
- Agent 03 — Approval Workflow for budget change approvals

---

## What It Produces

- **Financial baseline**: the approved budget stored as a permanent reference
- **Cost tracking register**: actual costs recorded against each cost category and work package
- **Forecast (EAC/ETC)**: current estimate of total and remaining project cost
- **Variance analysis**: cost variance at project, work package, and cost category level
- **EVM metrics**: SV, CV, SPI, CPI, and related schedule and cost performance indices
- **Budget threshold alerts**: notifications when spending approaches or exceeds defined thresholds
- **Financial dashboard**: real-time financial summary for the project and portfolio
- **Profitability analysis**: ROI and IRR tracking against the business case commitment
- **Financial reports**: structured period-end reports for governance and finance review

---

## How It Appears in the Platform

The financial picture is surfaced primarily through the **Dashboard Canvas**, where a financial summary panel shows the budget, actuals to date, forecast at completion, and variance percentage. The colour coding gives an immediate health indication — green for on-budget, amber for approaching tolerance, red for exceeding tolerance.

The detailed financial breakdown — cost category analysis, work package costs, EVM metrics — is accessible from the financial section of the project workspace, presented as a structured dashboard with drill-down capability. The Spreadsheet Canvas is available for teams that prefer to review financial data in a tabular format.

The assistant panel can answer financial questions directly: "What is our current cost variance?" "How much budget do we have remaining?" "What is our forecast at completion?" — returning current figures in a conversational format.

---

## The Value It Adds

Financial overruns are one of the most common failure modes in project delivery, and they almost always involve a period of wilful ignorance — the project team knowing the numbers are bad but not having a mechanism to surface and address the issue before it escalates. The Financial Management agent eliminates this by providing continuous, automated financial monitoring that makes variances visible in real time and alerts the right people before thresholds are breached.

For portfolio leaders, the aggregated financial view across all projects — budget versus actuals versus forecast — is essential for managing the organisation's investment effectively. This view is typically only available at month-end in most organisations. The platform makes it available continuously.

---

## How It Connects to Other Agents

The Financial Management agent receives its baseline from **Agent 05** (business case) and adjustments from **Agent 17** (change management). It provides financial performance data to **Agent 09 — Lifecycle and Governance** for health scoring and to **Agent 22 — Analytics and Insights** for portfolio financial reporting. Budget overrun risks are surfaced to **Agent 15 — Risk and Issue Management** as financial risks. **Agent 07 — Programme Management** uses it for programme-level financial consolidation.
