# Agent 6: Portfolio Strategy & Optimization Agent Specification

## Purpose

The Portfolio Strategy & Optimization Agent manages the composition and allocation of the project and program portfolio. Its primary goal is to maximise strategic value and business outcomes while respecting resource and budget constraints. By combining strategic alignment scoring, multi‑criteria prioritisation and optimisation algorithms, this agent ensures that the right mix of initiatives is approved and funded.

## Key Capabilities

Portfolio prioritisation: Applies multi‑criteria decision analysis to rank proposals and active projects based on strategic fit, financial value, risk, resource feasibility and other weighted factors.

Strategic alignment scoring: Links each initiative to strategic objectives by analysing corporate strategy documents and business goals, assigning alignment scores.

Capacity‑constrained optimisation: Runs optimisation models to maximise portfolio value given resource and budget limits.

Risk/reward balancing: Balances high‑risk/high‑reward projects with lower‑risk initiatives to ensure a sustainable pipeline.

Scenario planning & what‑if analysis: Generates alternate portfolios under different budget, capacity or strategic priority scenarios and compares their projected outcomes.

Portfolio rebalancing recommendations: Suggests periodic adjustments to the portfolio mix to maintain the desired balance between innovation, operations and compliance.

Investment mix optimisation: Optimises the mix of innovation, operational and compliance initiatives to align with organisational targets.

## AI Technologies

Multi‑objective optimisation algorithms: Utilises evolutionary algorithms (e.g., NSGA‑II, MOGA) to find Pareto‑optimal portfolios balancing value, risk and resource use.

Machine‑learning strategic fit models: Trains models to estimate strategic alignment scores based on project descriptions and historical outcomes.

Predictive portfolio value modelling: Forecasts expected financial and strategic value for proposed projects using historical data and market conditions.

Constraint satisfaction programming: Allocates limited resources and budgets while meeting mandatory constraints (e.g., minimum compliance spend).

NLP analysis of strategic documents: Extracts objectives and priorities from corporate strategy papers, OKRs and vision statements to inform scoring.

## Methodology Adaptations

Agile Portfolios: Focuses on value‑stream mapping, flow metrics and incremental delivery. Optimisation considers sprint capacity and prioritises value delivered per iteration.

Waterfall Portfolios: Emphasises phase‑gate alignment and resource leveling. Projects are evaluated on phase completion and long‑term resource forecasts.

Hybrid Portfolios: Balances both approaches, combining iterative value delivery with gated governance.

## Dependencies & Interactions

Business Case & Investment Analysis Agent (Agent 5): Supplies completed business cases with ROI and benefit projections.

Program Management Agent (Agent 7): Provides program structures and dependencies for portfolio alignment.

Resource & Capacity Management Agent (Agent 11): Supplies capacity and skills availability for optimisation.

Financial Management Agent (Agent 12): Provides budget constraints and cost baselines.

Risk Management Agent (Agent 15): Supplies risk scores for proposed and active projects.

Strategic Planning Tools: Integrates with platforms such as Cascade or AchieveIt to import organisational objectives and OKRs.

## Integration Responsibilities

Planview/Clarity PPM: Retrieve and update portfolio data, including active project lists, resource capacity and financial allocations.

Strategic Planning Systems: Pull corporate objectives and scorecard targets to calculate alignment scores.

Financial Systems: Read budget ceilings, cost centre allocations and funding availability for each fiscal period.

HRIS: Obtain resource availability and skill mix for capacity constraints.

Publish Events: Emit events such as portfolio.prioritised, portfolio.rebalanced or portfolio.scenario.generated on Service Bus/Event Grid for downstream agents.

## Data Ownership

Portfolio composition & rankings: Authoritative source for the current ranked portfolio of projects and programs.

Strategic alignment scores: Stores calculated scores for each project against each strategic objective.

Optimisation scenarios: Maintains archives of scenario inputs, outputs and chosen solutions.

Portfolio performance metrics: Tracks delivered value, strategic coverage and realised benefits across the portfolio.

## Key Workflows

**Portfolio Prioritisation:** When a new business case is approved, the agent gathers strategic objectives, current portfolio composition, available capacity and budget information. It evaluates the new proposal against weighted criteria (strategic alignment, ROI, risk, resource feasibility) and runs the optimisation model to recompute the ranked portfolio. The resulting ranking and justification are presented to the portfolio governance board for decision.

**Portfolio Rebalancing:** At regular intervals (e.g., quarterly), the agent analyses the current portfolio mix against target allocations (innovation, operations, compliance). It identifies gaps and recommends actions such as accelerating completion of operational projects or approving new innovation proposals. Recommendations include quantified impacts on strategic score and capacity utilisation.

**Scenario Planning:** Portfolio managers request what‑if analyses (e.g., “What if budget is cut by 10%?”). The agent runs optimisation under new constraints and compares resulting portfolios, highlighting trade‑offs in value, risk and strategic coverage. Users can iteratively refine scenarios via the assistant.

## UI/UX Design

Portfolio Dashboard: An interactive dashboard in the main canvas displays the ranked portfolio, alignment scores and resource utilisation. Users can adjust weighting sliders (e.g., strategic value vs. ROI) and immediately see updated rankings.

Scenario Builder Canvas: A separate tab lets users define scenarios by modifying budgets, capacity or strategic priorities. The agent visualises differences between scenarios with bar charts and spider graphs.

Recommendation Card: Summarises optimisation outcomes with recommended actions (approve, defer, cancel), alignment rationale and projected benefits.

Governance Workflow Integration: Portfolio governance board members receive interactive cards in the assistant panel to approve or modify portfolio recommendations.

## Configuration Parameters

Criteria Weights: Default weighting for alignment, ROI, risk, resource feasibility and compliance (configurable per organisation).

Resource & Budget Constraints: Maximum spending caps per fiscal period, minimum innovation investment percentages, capacity buffers.

Optimisation Algorithm Settings: Number of generations, population size and convergence criteria for evolutionary algorithms.

Rebalancing Frequency: Schedule (e.g., quarterly, monthly) and triggers (e.g., major strategy change) for portfolio rebalancing.

Strategic Objective Mapping: Mapping of strategic objectives to scoring rubrics and weights.

## Azure Implementation Guidance

Compute & Orchestration: Implement optimisation logic as a combination of Azure Functions (for lightweight scoring) and Azure Machine Learning pipelines (for training and running multi‑objective optimisation models). Use Azure Durable Functions to orchestrate long‑running optimisation workflows and scenario analyses.

Data Storage: Store portfolio data, alignment scores and scenario results in Azure SQL Database or Cosmos DB (with graph support for relationships). Use Azure Data Lake Storage for historical scenario archives.

AI Services: Use Azure Cognitive Services for NLP of strategic documents and Azure ML for predictive portfolio value models. Host evolutionary algorithms within ML workspaces.

Integration: Use Azure Logic Apps or Data Factory to connect to Planview, Clarity, financial systems, HRIS and strategic planning tools via connectors. Ingest corporate strategy documents into Azure Cognitive Search for objective extraction.

Messaging: Use Azure Service Bus or Event Grid to publish portfolio events and subscribe to upstream events (e.g., business_case.approved).

Security: Protect sensitive strategic data using Azure Key Vault for credentials and secrets. Enforce role‑based access control (RBAC) at the database and function levels. Enable encryption at rest and in transit (TLS).

Monitoring: Instrument optimisation runs with Application Insights and Log Analytics. Track model performance, algorithm convergence and resource usage.

## Security & Compliance

Ensure that strategic objectives, portfolio rankings and budget information are accessible only to authorised portfolio managers and executives.

Log all changes to criteria weights and portfolio decisions for auditability; maintain an immutable record in Azure Storage.

Comply with enterprise data governance policies by anonymising sensitive project data when used in machine‑learning models.

Enforce segregation of duties between portfolio planners and approvers; integrate with the Compliance & Security Agent for policy checks.

## Performance & Scalability

Batch vs. Interactive Processing: Optimisation runs can be resource‑intensive. Pre‑compute baseline rankings during off‑peak hours and support on‑demand scenario runs with smaller population sizes for responsiveness.

Caching: Cache frequently accessed alignment scores and ROI predictions to reduce compute load.

Parallelism: Leverage Azure ML’s parallel computing capabilities to evaluate portfolios concurrently. Use asynchronous event‑driven architecture to avoid blocking user interactions.

## Logging & Monitoring

Log all optimisation runs, including inputs, outputs, algorithm parameters and execution time for audit and troubleshooting.

Monitor key metrics such as optimisation convergence, response times, error rates and utilisation of compute resources via the System Health & Monitoring Agent.

Publish portfolio decision events with contextual data to enable downstream analytics and benefit realisation tracking.
