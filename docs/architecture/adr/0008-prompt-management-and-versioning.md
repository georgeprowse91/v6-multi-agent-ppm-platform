# ADR 0008: Prompt Management and Versioning

## Status

Accepted.

## Context

Prompt templates must be versioned, validated, and traceable to support deterministic LLM behavior in development and production. Prompt changes should remain auditable alongside the rest of the repository.

## Decision

Store prompt templates under `agents/runtime/agents/runtime/prompts/` and validate them against a JSON schema. Prompts are versioned in Git and loaded by the prompt registry. Redaction rules are embedded in prompt metadata to prevent sensitive data exposure.

## Consequences

- Prompts are part of the codebase and can be reviewed and tested.
- Version control provides traceability for prompt changes.
- A future promotion workflow (dev → prod prompts) will require additional tooling.

## References

- `agents/runtime/agents/runtime/prompts/examples/intent-router.prompt.yaml`
- `agents/runtime/agents/runtime/prompts/schema/prompt.schema.json`
- `agents/runtime/agents/runtime/prompts/prompt_registry.py`
