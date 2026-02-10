# State Management and Unified Memory

## Overview

The platform now uses a **unified memory service** to persist and retrieve shared context between agents and orchestrator task executions. This reduces ad-hoc context passing and improves state consistency.

## Memory lifecycle

1. The orchestrator resolves a memory key (typically correlation/conversation ID).
2. Existing context is loaded from memory before task execution.
3. Each agent task reads merged context and dependency outputs.
4. After task completion, orchestrator appends history/outputs/insights and persists context.
5. Base agents can also save/load per-agent scoped context using `conversation_id:agent_id` keys.

## Retrieval hygiene

- Context is namespaced by memory key to avoid accidental cross-conversation leakage.
- Agent-local entries use conversation + agent identifiers.
- The orchestrator normalizes insights and keeps task output lineage in `agent_outputs`.
- TTL can be configured to evict stale context and avoid context pollution.

## Privacy and data handling

- Store only operationally necessary context.
- Avoid saving raw secrets or PII unless required by policy.
- Use TTL for temporary conversation state to reduce retention duration.
- Prefer sanitized summaries over full payloads for long-term persistence.

## Components

- `services/memory_service/memory_service.py`: in-memory + SQLite memory backend with optional TTL.
- `packages/memory_client.py`: client wrapper used by orchestrator and agents.
- `agents/runtime/src/base_agent.py`: memory helper methods (`save_context`, `load_context`).
- `agents/runtime/src/orchestrator.py`: centralized context persistence during DAG execution.
