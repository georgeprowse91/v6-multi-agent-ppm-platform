# Security & Architecture Review — February 2026

**Scope:** Full repository review of the Multi-Agent PPM Platform (v4).
**Reviewer:** Senior Software Architect / AI Engineer.
**Branch:** `claude/review-ppm-platform-cknWG`

---

## 1. Executive Summary

The Multi-Agent PPM Platform is a well-structured, enterprise-grade AI-native Project Portfolio Management system featuring 25 specialised agents, 16 microservices, a React 18 frontend, 45+ connector integrations, and a comprehensive operational stack (Kubernetes, Helm, Terraform, OpenTelemetry). The codebase demonstrates strong foundational architecture across observability, access control, event-driven orchestration, and multi-methodology delivery support.

This review identified **four actionable improvements** spanning security, cloud-provider coverage, and AI safety. All four have been implemented and tested.

---

## 2. Review Findings

### 2.1 Missing Content-Security-Policy (CSP) Header *(Critical — Security)*

**File:** `packages/security/src/security/headers.py`

**Issue:** The `SecurityHeadersMiddleware` set seven security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy, Cross-Origin-Resource-Policy, Strict-Transport-Security) but omitted the `Content-Security-Policy` header entirely.

**Impact:** Without CSP, the platform has no browser-enforced defence against cross-site scripting (XSS) attacks delivered via the web console. This non-compliance affects:
- Australian Government ISM control SC-SC-18 (Content Security)
- APRA CPS 234 clause 36 (controls for cyber incidents)
- OWASP Top 10 A03:2021 – Injection

**Fix applied:**
- Introduced `_build_csp()` helper that assembles a strict CSP directive set: `default-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'self'`, `form-action 'self'`, `upgrade-insecure-requests`, plus conservative script/style/image/font policies.
- Added `csp_extra_script_srcs` constructor parameter (and `CSP_EXTRA_SCRIPT_SRCS` environment variable) so operators can extend the script allowlist for approved CDN sources without modifying code.
- The directive is applied via `response.headers.setdefault()` (consistent with all other security headers) so individual responses can override it if required.

---

### 2.2 OIDC Discovery Cache Memory Leak & Stale-Data Risk *(High — Security / Reliability)*

**File:** `apps/api-gateway/src/api/middleware/security.py`

**Issue:** The module-level `_OIDC_CONFIG_CACHE` was declared as a plain `dict[str, dict[str, Any]] = {}`. This implementation:
1. **Never evicts entries** — in a long-running process handling many tenants or rotating IdP endpoints, the dict grows without bound.
2. **Never expires entries** — after an IdP rotates its JWKS or changes its discovery document, the gateway continues using the stale cached version until the process restarts. This can cause authentication failures or, in edge cases, acceptance of tokens signed by revoked keys.
3. **Not thread-safe** — concurrent async tasks writing to the dict can produce corrupted state (dict resize race).

Note: the `packages/security/src/security/auth.py` package *already has* a proper TTL cache (`_TTLCache`). The middleware was an inconsistent duplicate that missed the improvement.

**Fix applied:**
- Replaced `_OIDC_CONFIG_CACHE: dict = {}` with `_OIDCTTLCache`, a thread-safe, bounded LRU cache with per-entry TTL.
- Default TTL: 300 seconds (matching `AUTH_CACHE_TTL_SECONDS` env var used by the security package).
- Default max size: 32 entries (configurable via `AUTH_CACHE_MAX_ENTRIES`).
- The cache uses `threading.RLock` for mutual exclusion, consistent with the security package implementation.
- Eviction uses LRU order (Python `OrderedDict.popitem(last=False)`).

---

### 2.3 Missing Azure OpenAI Provider *(High — Compliance / Sovereignty)*

**Files:**
- `packages/llm/src/providers/azure_openai_provider.py` *(new)*
- `packages/llm/src/router.py` *(updated)*
- `apps/web/data/llm_models.json` *(updated)*

**Issue:** The LLM router supported three providers — `openai`, `anthropic`, and `google` — but not Azure OpenAI. For Australian Government and regulated-enterprise deployments, Azure OpenAI is the *required* provider because it:
- Keeps data within Azure Australia East / Southeast Asia regions (Privacy Act 1988 APP 8, ISM control SC-SC-13).
- Is the only option for PROTECTED-level workloads (IRAP-assessed, ISM compliant).
- Satisfies APRA CPS 234 data locality requirements.
- Supports Private Endpoint connectivity, eliminating data egress over the public internet.

**Fix applied:**
- Created `AzureOpenAIProvider` with the same `complete()` interface as existing providers.
- Uses Azure OpenAI's deployment-scoped URL (`/openai/deployments/{deployment_id}/chat/completions?api-version=…`) and the `api-key` header (Azure subscription key, not the OpenAI user key).
- Configured via `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, and `AZURE_OPENAI_API_VERSION` environment variables.
- Added `azure_openai` branch to `LLMRouter._build_adapter()` with the same error-handling pattern as other providers.
- Registered two disabled-by-default model entries in `llm_models.json` (`gpt-4o` and `gpt-4o-mini`) that operators enable by setting `"enabled": true` alongside the required environment variables.

---

### 2.4 Insufficient Prompt Injection Detection *(Medium — AI Safety)*

**File:** `packages/llm/prompt_sanitizer.py`

**Issue:** The original detection had seven regex patterns covering classic override phrases. It missed:
- `forget previous instructions` / `disregard instructions` variants
- Credential/env exfiltration (`Print env`, `show environment variables`)
- Safety bypass phrasings (`bypass safety filter`, `disable safety guardrail`)
- Modern jailbreak personas (`DAN mode`, `jailbreak`, `Act as unrestricted`)
- Structured template injection markers used to abuse LLM chat templates (`[INST]`, `<|im_start|>`, `<|system|>`)
- Unicode homoglyph bypass: full-width Latin characters (e.g. `ＩＧＮＯＲＥ`) are visually identical to ASCII but bypass regex matching on the raw string.

**Fix applied:**
- Added 11 new regex patterns covering the categories above.
- Added a `_normalise()` helper that applies NFKC Unicode normalisation before pattern matching, collapsing lookalike characters.
- `detect_injection()` now normalises before matching; `sanitize_prompt()` normalises before phrase substitution.
- Updated `ATTACK_PHRASES` tuple with additional neutralisation targets for the sanitizer.
- Added docstring explaining the two-layer strategy (normalisation → pattern matching).

---

## 3. Unchanged Findings (Noted, Not Implemented)

The following observations are architectural notes for the engineering team:

| # | Area | Observation | Recommendation |
|---|------|-------------|----------------|
| 1 | Auth code duplication | JWT validation logic exists in both `packages/security/src/security/auth.py` (with `_TTLCache`) and `apps/api-gateway/src/api/middleware/security.py` (now also fixed). Both serve the same function. | Refactor the middleware to delegate entirely to the security package's `authenticate_request()` / `_validate_jwt()`, eliminating the duplicate. |
| 2 | `sys.path` manipulation | Multiple files use `sys.path.insert(0, ...)` for intra-repo imports. This is fragile and breaks IDE tooling. | Migrate to proper Python packaging with `pyproject.toml` `[tool.setuptools.packages.find]` or `namespace_packages`, or use a monorepo tool like Pants/Bazel that handles import paths properly. |
| 3 | LLM key rotation | LLM API keys are resolved per-request from environment variables. There is no in-process rotation trigger. | Integrate with the existing `services/scope_baseline/` secret rotation job or add a webhook/signal handler that calls `resolve_secret()` and invalidates the adapter cache. |
| 4 | Model registry `lru_cache` | `load_model_registry()` uses `@lru_cache(maxsize=1)` with no invalidation mechanism. New model entries or registry updates require a process restart. | Add a `clear_model_registry_cache()` call-path reachable from the admin API for zero-downtime registry updates (already exists as `clear_model_registry_cache()` in the test helpers — wire it up to an admin endpoint behind a `config.write` permission gate). |
| 5 | `on_event` deprecation | `app.on_event("startup")` and `app.on_event("shutdown")` in the API gateway use the FastAPI 0.93+ deprecated decorator. | Migrate to `@asynccontextmanager` lifespan pattern (FastAPI docs §Lifespan Events). |

---

## 4. Test Coverage Added

| Test file | Coverage |
|-----------|----------|
| `tests/security/test_security_headers.py` | CSP directive construction, header presence, HSTS behaviour, env-var extension |
| `tests/security/test_oidc_cache.py` | TTL expiry, LRU eviction, thread-safety, boundary conditions |
| `packages/llm/tests/test_azure_openai_provider.py` | Successful completion, JSON mode, URL correctness, timeout/4xx/429 error handling, API key header, router adapter construction |
| `tests/llm/test_prompt_sanitizer_enhanced.py` | 23 positive/negative detection cases, Unicode normalisation, sanitize phrase neutralisation, false-positive guard |

---

## 5. Architecture Assessment

### Strengths
- **25 specialised agents** with clear separation of concerns, lifecycle hooks, policy evaluation, cost tracking, and observability.
- **Circuit breaker + retry** in the orchestrator with dependency-aware DAG execution.
- **Immutable audit trail** in a dedicated service with separate storage.
- **Field-level masking** middleware prevents over-exposure of sensitive response data.
- **7 methodology templates** (Waterfall, Agile, PRINCE2, SAFe, Hybrid, Lean, Kanban) with gate-phase enforcement.
- **45+ connectors** covering major enterprise tools.
- **Comprehensive CI/CD** with 22 GitHub Actions workflows including SBOM, container scanning, SAST, secret scanning, and IaC scanning.
- **OpenTelemetry-first** instrumentation with distributed tracing, metrics, and structured logging.

### Production Readiness Score (pre-improvements)
| Category | Assessment |
|----------|-----------|
| Architecture | ✅ Strong |
| Observability | ✅ Strong |
| Security headers | ⚠️ Missing CSP (now fixed) |
| Auth cache | ⚠️ Memory leak (now fixed) |
| AI safety | ⚠️ Partial injection coverage (now improved) |
| Cloud compliance (AUS) | ⚠️ No Azure OpenAI (now added) |
| Test coverage | ✅ 320+ test files |
| Documentation | ✅ Comprehensive |

---

## 6. Change Summary

| File | Type | Description |
|------|------|-------------|
| `packages/security/src/security/headers.py` | Modified | Added CSP header with strict directive set and operator-extensible script-src |
| `apps/api-gateway/src/api/middleware/security.py` | Modified | Replaced unbounded plain-dict OIDC cache with thread-safe TTL LRU cache |
| `packages/llm/src/providers/azure_openai_provider.py` | New | Azure OpenAI provider for data-sovereign enterprise/government deployments |
| `packages/llm/src/router.py` | Modified | Added `azure_openai` provider branch and import |
| `apps/web/data/llm_models.json` | Modified | Registered two Azure OpenAI model entries (disabled by default) |
| `packages/llm/prompt_sanitizer.py` | Modified | 11 new injection patterns + Unicode normalisation layer |
| `tests/security/test_security_headers.py` | New | Test suite for CSP header middleware |
| `tests/security/test_oidc_cache.py` | New | Test suite for OIDC TTL cache |
| `packages/llm/tests/test_azure_openai_provider.py` | New | Test suite for Azure OpenAI provider |
| `tests/llm/test_prompt_sanitizer_enhanced.py` | New | Test suite for enhanced injection detection |
