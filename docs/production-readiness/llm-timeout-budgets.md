# LLM Timeout Budgets

This document describes the timeout hierarchy for LLM-related operations and recommended production values.

## Timeout hierarchy

Requests flow through multiple timeout layers. Each outer layer must be longer than its inner layers to avoid masking errors.

```
HTTP client (browser/mobile)
  -> Application Gateway (request_timeout: 30s)
    -> API Gateway (uvicorn request timeout)
      -> Agent Orchestrator (AGENT_CALL_TIMEOUT: 30s)
        -> LLM Provider call (LLM_TIMEOUT: 10s)
```

### Layer details

| Layer | Env var / Config | Default | Location |
|-------|-----------------|---------|----------|
| Application Gateway | `request_timeout` | 30s | `ops/infra/terraform/main.tf` — `backend_http_settings` |
| Agent orchestrator | `AGENT_CALL_TIMEOUT` | 30.0s | `services/orchestration-service/helm/values.yaml` |
| LLM provider call | `LLM_TIMEOUT` | 10s | `packages/llm/src/llm/client.py:386` |
| LLM router | `timeout` (constructor) | 10.0s | `packages/llm/src/llm/router.py:31` |
| Pytest test timeout | `timeout` | 60s | `pyproject.toml` `[tool.pytest.ini_options]` |

## Token budget management

The `TokenBudgetManager` class (`packages/llm/src/llm/client.py:189`) enforces per-tenant token limits:

- **Configuration**: Pass `token_budgets` dict in LLM client config (e.g., `{"tenant_a": 100000}`)
- **Estimation**: `TokenBudgetManager.estimate_tokens()` uses word-count heuristic (tokens ~ words * 1.3)
- **Enforcement**: `ensure_budget()` raises `TokenBudgetExceeded` before sending requests that would exceed limits

## Production recommendations

### LLM timeout

Set `LLM_TIMEOUT=30` for production to accommodate:
- Complex multi-step agent flows that chain multiple LLM calls
- Azure OpenAI regional latency variation
- Rate-limit retry backoff (client retries up to `max_attempts` with exponential backoff)

### Timeout chain rule

Each outer timeout must be at least **2x** the inner timeout:
- `LLM_TIMEOUT=30` -> `AGENT_CALL_TIMEOUT=60` -> App Gateway `request_timeout=120`

### Token budgets

Configure per-tenant budgets in production to prevent runaway costs:
```json
{
  "token_budgets": {
    "default": 500000,
    "enterprise_tenant": 2000000
  }
}
```

## Environment variable reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LLM_TIMEOUT` | float (seconds) | 10 | Timeout for individual LLM provider calls |
| `AGENT_CALL_TIMEOUT` | float (seconds) | 30.0 | Timeout for agent-to-agent orchestration calls |
| `LLM_PROVIDER` | string | `azure_openai` | Active LLM provider backend |
| `AZURE_OPENAI_ENDPOINT` | string | — | Azure OpenAI service endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | string | — | Model deployment name |
| `OPENAI_BASE_URL` | string | `https://api.openai.com/v1` | OpenAI API base URL |
| `ANTHROPIC_BASE_URL` | string | `https://api.anthropic.com/v1` | Anthropic API base URL |
