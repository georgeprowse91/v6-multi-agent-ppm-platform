# Security Architecture

## Prompt injection detection and sanitisation

The runtime applies prompt injection checks to inbound user-authored prompt fields before agent processing.

### Detection rules

`packages/llm/prompt_sanitizer.py` implements heuristic pattern checks for common attacks, including:

- attempts to ignore or override system/developer instructions,
- attempts to reveal secrets, credentials, hidden prompts, or chain-of-thought,
- role-escalation language (for example, pretending to be an admin),
- obfuscation hints around decoding hidden prompt material.

`detect_injection(prompt: str) -> bool` returns `True` if any of these patterns match.

### Sanitisation rules

`sanitize_prompt(prompt: str) -> str` neutralises known attack phrases and high-risk formatting patterns by:

- replacing known injection phrases with `[REMOVED_INJECTION_PHRASE]`,
- neutralising triple-backtick blocks,
- HTML-encoding angle brackets.

### BaseAgent enforcement flow

`agents/runtime/src/base_agent.py` evaluates candidate prompt fields during `execute()`.

- If injection is detected and `allow_injection: false` (default), execution is rejected with a safe user-facing error.
- If injection is detected and `allow_injection: true`, the prompt is sanitised and processing continues.
- Audit/structured logs include detection metadata: detected fields, sanitised fields, and enforcement mode.

### Configuration

Per-agent behaviour is configurable in agent YAML files (for example `ops/config/agents/intent-router.yaml`):

```yaml
allow_injection: false
prompt_fields:
  - prompt
  - user_prompt
  - query
```

- `allow_injection` controls reject (`false`) vs sanitise-and-continue (`true`).
- `prompt_fields` defines which input keys are inspected.
