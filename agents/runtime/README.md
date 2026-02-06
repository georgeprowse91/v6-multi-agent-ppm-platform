# Runtime

## Overview

The runtime package provides the shared execution infrastructure for all agents -- including the orchestrator loop, base agent class, state management, event bus, and supporting services. It also houses the evaluation framework and prompt template registry.

## Directory structure

| Name | Description | Link |
|------|-------------|------|
| `eval` | Evaluation framework for testing and benchmarking agent behaviour. | [./eval/](./eval/) |
| `prompts` | Prompt templates, a prompt registry, example prompts, and schema definitions. | [./prompts/](./prompts/) |
| `src` | Core runtime implementation including the orchestrator, base agent, state store, and event bus. | [./src/](./src/) |

## Key files

| File | Description |
|------|-------------|
| `__init__.py` | Python package initialiser for the runtime module. |
| `src/orchestrator.py` | Main orchestration loop that dispatches work to agents. |
| `src/base_agent.py` | Abstract base class all agents inherit from. |
| `src/state_store.py` | Persistent state storage used by agents between invocations. |
| `src/event_bus.py` | Publish-subscribe event bus for inter-agent communication. |
| `src/agent_catalog.py` | Programmatic access to the agent catalogue at runtime. |
| `src/data_service.py` | Shared data access layer used by agents. |
| `src/memory_store.py` | In-memory store for short-lived conversational context. |
| `src/models.py` | Pydantic/dataclass models shared across the runtime. |
| `src/policy.py` | Policy definitions governing agent behaviour and access control. |
| `src/audit.py` | Audit logging for agent actions and decisions. |
