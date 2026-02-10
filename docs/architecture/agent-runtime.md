# Agent Runtime

## Purpose

Define the AgentRun lifecycle, orchestrator state transitions, and transparency surfaces that
expose progress and auditability to product interfaces and operators. This document complements
[Agent Orchestration](agent-orchestration.md) and the runtime package overview in
[`agents/runtime/README.md`](../../agents/runtime/README.md).

## AgentRun Lifecycle

Agent runs move through explicit, observable states that the orchestrator and UI can surface.
The canonical lifecycle is:

- **queued**: A request has been accepted, persisted, and is waiting for orchestration resources.
- **running**: The orchestrator is actively dispatching work to one or more agents.
- **blocked**: Execution is paused pending input (human approval, missing data, or external
  dependency resolution).
- **completed**: The run finished successfully and emitted a final response.
- **failed**: The run terminated due to an error, timeout, or policy violation.

State transitions are recorded in the runtime audit log and published on the event bus so downstream
services can render progress or trigger follow-up actions.

## Orchestrator Interaction Model

The orchestrator loop coordinates AgentRun transitions and publishes state changes through runtime
hooks.

1. **Queue intake**: The runtime accepts a request, assigns an AgentRun ID, and sets the state to
   `queued`.
2. **Dispatch**: The orchestrator moves the run to `running`, selects agents per the orchestration
   plan, and invokes tool execution.
3. **Block handling**: If approvals, data dependencies, or guardrails prevent execution, the
   orchestrator emits a `blocked` transition and registers the blocking reason.
4. **Resolution**: Once blocking conditions clear, the orchestrator resumes and returns to
   `running`.
5. **Completion**: The orchestrator records either `completed` or `failed` and emits the final
   response payload.

Runtime hooks include audit logging, event bus publication, and state store updates so that
orchestration transitions remain consistent across the runtime stack.

## Audit & Event Surfaces

Transparency relies on durable, queryable surfaces:

- **Audit log**: Each transition, tool call, and policy decision is written to the runtime audit
  facility (`agents/runtime/src/audit.py`) for compliance and troubleshooting.
- **Event bus**: The runtime publishes transition events to the event bus so downstream subscribers
  can react in near real time.
- **State store**: The state store persists AgentRun metadata, including the latest lifecycle
  state and blocking reason, for UI queries.

## UI Surfaces

Product interfaces should surface AgentRun state and context to users:

- **Progress indicators**: Show queued, running, blocked, completed, and failed states with clear
  messaging and timestamps.
- **Explanations**: Provide human-readable summaries of why a run is blocked or failed, drawing from
  audit metadata.
- **Async notifications**: Deliver notifications when a blocked run resumes or completes to avoid
  requiring continuous polling.

## Related Documentation

- [Agent Orchestration](agent-orchestration.md)
- [Runtime README](../../agents/runtime/README.md)
