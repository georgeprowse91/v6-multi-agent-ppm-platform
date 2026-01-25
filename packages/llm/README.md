# LLM Package

Shared LLM client helpers intended for agent runtime integration.

## Current state

- No package implementation yet in `packages/llm/`.
- Agent runtime integrations live under `agents/runtime/src/`.

## Quickstart

Inspect the agent runtime base agent:

```bash
sed -n '1,80p' agents/runtime/src/base_agent.py
```

## How to verify

```bash
ls agents/runtime/src
```

Expected output lists runtime modules used by agents.

## Key files

- `agents/runtime/src/`: current runtime implementation.
- `packages/llm/README.md`: scope and next steps.

## Example

Search for OpenAI client usage:

```bash
rg -n "openai" agents/runtime/src
```

## Next steps

- Add shared client wrappers in `packages/llm/src/`.
- Replace direct client calls in agents with the shared helpers.
