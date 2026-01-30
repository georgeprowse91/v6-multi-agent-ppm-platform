# AI Architecture

## Purpose

Describe the LLM provider abstraction, prompt management, and safety controls implemented in the platform.

## Architecture-level context

AI capabilities are provided through a shared LLM client package and prompt registry. Agent runtimes call the LLM client via the Intent Router and other domain agents. Prompt templates are stored and versioned in the repository for traceability and offline testing.

## Core building blocks

| Capability | Implementation | Notes |
| --- | --- | --- |
| LLM provider abstraction | `packages/llm/src/llm/client.py` | Supports `mock`, `openai`, and `azure-openai` providers. |
| Prompt registry | `agents/runtime/prompts` | YAML prompt definitions validated against `prompt.schema.json`. |
| Redaction rules | `agents/runtime/prompts/prompt_registry.py` | Redacts sensitive fields from prompt payloads. |
| Intent routing | `agents/core-orchestration/agent-01-intent-router` | Uses LLM responses to select agent plans. |

## Provider selection and configuration

- **Mock provider (default):** Uses `LLM_MOCK_RESPONSE` or `LLM_MOCK_RESPONSE_PATH` for deterministic outputs.
- **OpenAI provider:** Set `LLM_PROVIDER=openai` and configure `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`.
- **Azure OpenAI provider:** Set `LLM_PROVIDER=azure-openai` and configure `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`.

## Prompt management

Prompt YAML files include metadata and redaction rules. The prompt registry loads prompts by agent and purpose and validates them against the schema before use.

- Prompt examples: `agents/runtime/prompts/examples/*.prompt.yaml`
- Schema validation: `agents/runtime/prompts/schema/prompt.schema.json`

## Safety and guardrails

- **Redaction:** Prompt registry applies redaction rules to remove sensitive fields before sending data to LLM providers.
- **RBAC enforcement:** The API gateway and policy engine enforce permissions before agent execution.
- **Deterministic testing:** Mock responses enable reproducible runs in CI and local development.

## Verification steps

- List available prompt definitions:
  ```bash
  ls agents/runtime/prompts/examples
  ```
- Inspect the LLM provider selection logic:
  ```bash
  rg -n "LLM_PROVIDER" packages/llm/src/llm/client.py
  ```

## Implementation status

- **Implemented:** LLM client abstraction, mock/OpenAI/Azure providers, prompt registry with schema validation.
- **Implemented:** Prompt version promotion workflows and registry CLI tooling in `packages/llm`.

## Related docs

- [Agent Orchestration](agent-orchestration.md)
- [LLM Package README](../../packages/llm/README.md)
- [Security Architecture](security-architecture.md)
