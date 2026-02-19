# Agent 01 — Intent Router

**Category:** Core Orchestration
**Role:** Platform Dispatcher

---

## What This Agent Is

The Intent Router is the first point of contact for every user interaction in the platform. It sits at the front of the agent network and acts as an intelligent dispatcher — reading what a user has asked for, working out what they actually mean, and directing that request to the right combination of specialist agents to handle it.

It operates invisibly. Users never interact with the Intent Router directly. They type a message or trigger an action in the workspace, and the Intent Router processes that input before anything else happens. The quality of the whole platform experience depends on this agent doing its job well: if it misreads the user's intent, the wrong agents respond. If it reads it correctly, the right expertise is assembled in seconds.

---

## What It Does

When a user submits a request — whether typed in the assistant panel, submitted through a form, or triggered by a workflow event — the Intent Router receives that input and performs three things:

**It classifies the intent.** It reads the text and identifies what the user is trying to accomplish. Is this a request to create a new project? A question about portfolio health? A risk that needs to be logged? A budget that needs reviewing? The agent has been trained to recognise a wide range of project and portfolio management intents, from straightforward document creation tasks through to complex portfolio optimisation queries.

**It extracts the relevant parameters.** Beyond understanding the intent, the agent picks out the specific details embedded in the request: the project ID being referenced, the portfolio in scope, the currency or financial amount mentioned, the type of entity being asked about, the timeframe in question. These parameters are passed downstream so that the agents that respond have the context they need without the user having to repeat themselves.

**It determines which agents should respond.** Based on the classified intent and extracted parameters, the Intent Router produces a routing plan — a structured list of which domain agents need to be invoked, in what order, and with what inputs. This plan is handed to the Response Orchestration agent, which executes it.

---

## How It Works

The Intent Router uses a language model to interpret user input. It sends the user's message to the platform's LLM gateway and receives back a classification of the intent along with a confidence score. If the confidence is high, that classification is used. If the language model is unavailable or returns a low-confidence result, the agent falls back to a keyword-based classifier that uses pattern matching to make a best-effort determination without relying on the LLM.

The agent is also capable of detecting when a single request contains more than one intent — for example, a user asking to "create a project and generate a risk register" is really asking for two things at once. In those cases, the Intent Router identifies both intents and constructs a routing plan that addresses each of them.

Every classification decision is recorded in the platform's audit log, including which method was used (LLM or fallback), the confidence score assigned, and the routing plan produced. This creates a complete, traceable record of how the system interpreted every user request.

---

## What It Uses

- The platform's LLM gateway to perform intent classification
- A fine-tuned transformer model for natural language understanding
- spaCy for named entity recognition, used to extract parameters such as project names, financial figures and entity types
- A keyword-based fallback classifier for resilience when the LLM is unavailable
- The audit log service to record every classification decision

---

## What It Produces

The Intent Router produces a **routing plan**: a structured document that specifies which agents should be called, with what parameters, and in what sequence. This plan is consumed by the Response Orchestration agent and drives everything that happens next.

It also emits an audit event for every request it processes, capturing the intent classification result, the confidence level, and whether the LLM or fallback method was used.

---

## How It Appears in the Platform

The Intent Router itself has no visible presence in the user interface. Its work happens behind the scenes the moment a user submits any input to the assistant panel or triggers an action. The speed with which the platform responds — and the relevance of that response — reflects the Intent Router's performance.

In the platform's administration console, operators can view agent execution logs that show how requests were classified and routed. This is useful for diagnosing unexpected behaviour or tuning the routing configuration.

---

## The Value It Adds

The Intent Router is what makes the platform feel intelligent rather than mechanical. Without it, users would need to navigate menus, select specific functions and fill in structured forms to get anything done. With it, they can describe what they need in plain language and the platform works out the rest.

It also provides resilience: by maintaining a fallback classifier alongside the LLM-based approach, the agent ensures that the platform continues to function and route requests correctly even when the language model is temporarily unavailable.

---

## How It Connects to Other Agents

The Intent Router feeds its output directly into **Agent 02 — Response Orchestration**, which takes the routing plan and executes it by calling the relevant domain agents. Every request that enters the platform flows through Agent 01 first. It does not communicate directly with domain agents; that is the responsibility of the orchestration layer.
