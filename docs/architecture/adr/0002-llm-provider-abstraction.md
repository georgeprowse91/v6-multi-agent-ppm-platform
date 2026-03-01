# ADR 0002: LLM Provider Abstraction

## Status

Accepted.

## Context

Agents must call LLMs during intent routing and response generation. The platform needs a provider-agnostic client to support mock responses in CI, OpenAI, and Azure OpenAI without rewriting agent logic.

## Decision

Implement a shared LLM client package (`packages/llm`) that selects a provider at runtime using environment variables. Supported providers:

- `mock` (deterministic testing)
- `openai` (HTTP API)
- `azure-openai` (Azure OpenAI HTTP API)

Agent runtimes call the LLM client and pass system/user prompts from the prompt registry.

## Consequences

- Agents do not embed provider-specific code.
- CI can run with deterministic mock responses.
- Runtime configuration governs provider choice and credentials.

## References

- `packages/llm/src/llm/client.py`
- `agents/core-orchestration/intent-router-agent/src/intent_router_agent.py`
- `docs/architecture/ai-architecture.md`
