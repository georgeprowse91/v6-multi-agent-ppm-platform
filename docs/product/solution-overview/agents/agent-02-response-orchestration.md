# Agent 02 — Response Orchestration

**Category:** Core Orchestration
**Role:** Execution Coordinator

---

## What This Agent Is

The Response Orchestration agent is the engine that makes multi-agent collaboration work. Once the Intent Router has classified a user's request and produced a routing plan, it is the Response Orchestration agent that picks up that plan and carries it through to completion — calling the right agents, in the right order, managing failures, caching results, and assembling everything into a single coherent response for the user.

It is the most operationally complex agent in the platform, responsible for coordinating the work of every other agent and ensuring that the user always receives a useful, well-structured answer regardless of how many underlying systems were involved in producing it.

---

## What It Does

**It executes the routing plan.** The agent receives a plan containing a set of tasks — each task specifying which domain agent should be called, what action it should perform, and what inputs it needs. The Response Orchestration agent works through this plan, calling each agent as directed.

**It manages parallel and sequential execution.** Not all tasks need to happen one after another. When tasks are independent of each other, the agent runs them simultaneously, which significantly reduces the time the user waits for a response. When one task depends on the output of another — for example, a financial forecast that depends on a schedule first being generated — the agent sequences those correctly, ensuring data flows in the right order.

**It handles failures gracefully.** If an agent call fails, the Response Orchestration agent retries it automatically using an exponential backoff strategy, giving the downstream system time to recover. If an agent consistently fails, a circuit breaker kicks in and prevents the system from continuing to flood a struggling service with requests. The user receives a partial response where possible, with a clear indication of what could not be completed.

**It caches results.** For tasks that are expensive to compute and are likely to be repeated — portfolio health summaries, resource utilisation snapshots — the agent caches the results for a configurable window (fifteen minutes by default). Repeat requests within that window are served from cache rather than re-invoking downstream agents, which improves response speed and reduces load on connected systems.

**It enriches responses with external research.** When configured, the agent can supplement the outputs of domain agents with information retrieved from external sources — market data, industry benchmarks, publicly available regulatory guidance — to provide richer, more contextually grounded responses.

**It aggregates and synthesises.** Once all agent calls in a plan have been completed, the Response Orchestration agent combines their outputs into a single, structured response. It resolves any conflicts between agent outputs, applies a consistent format, and presents the result to the user through the assistant panel.

---

## How It Works

The agent analyses the routing plan to build a dependency graph — a map of which tasks can run concurrently and which must wait for others to complete. It uses cycle detection to identify and handle any circular dependencies before execution begins.

Agent calls are made over HTTP to the individual agent services, with fallback options via the internal service registry or the event bus for agents that cannot be reached directly. The agent tracks the status of each task throughout execution and maintains a plan status that transitions from pending through to approved, in-progress, and completed.

All activity is recorded in the platform's observability layer, including per-task latency, cache hit and miss rates, retry counts, and failure reasons. This data feeds into the platform's performance dashboards and supports ongoing operational monitoring.

---

## What It Uses

- The routing plan produced by Agent 01 — Intent Router
- HTTP connections to each domain agent service
- An internal service registry for agent discovery
- The platform's event bus as a fallback communication channel
- A result cache with configurable time-to-live
- An external research integration for supplementary enrichment
- The platform's observability and metrics system
- The audit log service

---

## What It Produces

The Response Orchestration agent produces the **final response** that is returned to the user through the assistant panel. This may be a generated document, a summary report, a structured data table, a recommendation, or a confirmation that an action has been completed — depending on what was requested.

It also produces plan execution records showing the status, duration and outcome of every task in the routing plan, which are available to platform administrators through the agent runs monitoring view.

---

## How It Appears in the Platform

Like the Intent Router, the Response Orchestration agent operates entirely behind the scenes. Users see its output — the response that appears in the assistant panel — but not the coordination work that produced it.

In the administration console, the **Agent Runs** page shows a history of orchestration plans that have been executed, including the tasks they contained, the agents involved, the time taken, and any failures or retries that occurred. This gives operators a clear view of how the platform is performing and where bottlenecks exist.

---

## The Value It Adds

The Response Orchestration agent is what allows the platform to behave as a unified intelligent system rather than a collection of disconnected tools. A single user request can trigger five or six agent calls, each pulling data from a different system, and the user receives a single coherent answer in seconds. Without this coordination layer, users would have to navigate to each agent individually, interpret separate outputs, and assemble the picture themselves.

The caching mechanism also means that the platform is operationally efficient: heavily used views and reports are not recomputed from scratch on every request, and the connected source systems are not hammered with redundant queries.

---

## How It Connects to Other Agents

The Response Orchestration agent connects to every domain agent in the platform. It receives its instructions from **Agent 01 — Intent Router** and calls any combination of agents 03 through 25 depending on what the routing plan requires. It is the central coordination hub of the entire agent network.
