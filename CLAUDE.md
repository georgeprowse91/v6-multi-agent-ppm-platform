# CLAUDE.md — Multi-Agent PPM Platform

Guide for AI assistants working in this repository.

## Project overview

AI-native Project Portfolio Management (PPM) platform with 25 specialized agents orchestrating portfolio, program, and project delivery. The codebase is a Python + TypeScript monorepo targeting Azure cloud, with FastAPI backend services, a React 18 web console, and Kubernetes deployment via Helm charts.

- **Language**: Python 3.11+ (primary), TypeScript/React (web frontend), React Native (mobile)
- **License**: MIT
- **Cloud**: Azure (Azure OpenAI, Cosmos DB, Blob Storage, Service Bus, Key Vault)

## Repository layout

```
agents/                  25 domain agents + runtime scaffolding (BaseAgent, orchestrator)
apps/                    User-facing applications (web console, mobile, demo)
config/                  RBAC/ABAC policy definitions
connectors/              40 integration connectors + SDK + registry + MCP client
constraints/             Python version constraint files (e.g. py313.txt)
data/                    Canonical JSON schemas, migrations, quality rules, lineage, seed/demo data
docs/                    Architecture, methodology, agent catalog, onboarding docs
examples/                Scenario and configuration examples
integrations/            AI model, analytics, event bus, and persistence integration modules
ops/                     Scripts, tools, infra (Terraform, K8s), Docker, config files
packages/                Shared Python and TypeScript packages
services/                All backend microservices (API gateway, orchestration, workflow, and 18 others)
tests/                   Full test taxonomy: unit, integration, e2e, security, contract, load, performance
tools/                   Agent runner, connector runner, local dev tooling
vendor/                  Vendored stubs and third-party shims
```

## Build and development commands

### Installation

```bash
make install-dev          # Install dev + test dependencies, set up pre-commit hooks
cp ops/config/.env.example .env  # Then edit with your credentials
```

### Running locally

```bash
make dev-up               # Start local dev stack via Docker Compose (core profile)
make run-api              # API gateway at http://localhost:8000 (uvicorn with reload)
make run-web              # Web console at http://localhost:8501
```

### Testing

```bash
make test-unit            # Unit tests (excludes integration/e2e/security)
make test-integration     # tests/integration/
make test-e2e             # tests/e2e/
make test-security        # tests/security/
make test-all             # Full taxonomy: unit + integration + e2e + security
make test-cov             # Full suite with coverage (80% minimum gate)
```

Pytest is configured in `pyproject.toml` `[tool.pytest.ini_options]`. Default timeout is 60s per test. Tests use `--import-mode=importlib`. The `tests/conftest.py` bootstraps `sys.path` dynamically so all monorepo packages are importable.

### Linting and formatting

```bash
make lint                 # Ruff + Black + MyPy
make format               # Auto-format with Black + Ruff
```

### Quality gates and validation

```bash
make check                # lint + test + docs scans (links, placeholders, root layout, docs migration, connector maturity)
make ci-local             # Full CI check battery
make release-gate PROFILE=core  # Release maturity gate
make check-links          # Validate internal markdown links
make check-placeholders   # Scan for placeholder phrases in docs/configs
make check-security-baseline    # Minimum production security baseline
make secret-scan          # Gitleaks secret scanning
make env-validate         # Validate service environment config schemas
```

## Code style and conventions

### Python

- **Formatter**: Black (line-length 100, target py311)
- **Linter**: Ruff (rules: E, F, I, N, W, UP, G; E501 ignored — Black handles line length)
- **Type checker**: MyPy (strict-ish: `disallow_untyped_defs`, `warn_return_any`, `strict_optional`)
- **Docstrings**: Google-style
- **Logging**: Use parameterized logging (`logger.info("msg %s", val)`), never f-strings in logger calls (enforced by pre-commit hook)
- **Async**: Use `async`/`await` for I/O-bound operations; prefer `asyncio.gather()` for parallel work
- Python target version: 3.11 minimum, tested on 3.11, 3.12, and 3.13

### TypeScript / Frontend

- **Framework**: React 18 + TypeScript 5.3
- **Build**: Vite
- **State management**: Zustand
- **Routing**: React Router 6
- **Testing**: Vitest
- **Linting**: ESLint
- **Package manager**: pnpm (workspace defined in `pnpm-workspace.yaml`)

### Commit messages

Use conventional format: `<type>: <subject>` (e.g., `feat: Add risk prediction`, `fix: Resolve auth token expiry`)

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Branch naming

`feature/`, `fix/`, `docs/`, `refactor/`, `test/`

## Architecture

### Agent system (25 agents in 4 domains)

Agents live under `agents/` organized by domain:

**Core Orchestration** (`agents/core-orchestration/`)
- Intent Router — classifies user queries and routes to domain agents
- Response Orchestration — aggregates multi-agent responses
- Approval Workflow — orchestrates approval chains and task inboxes
- Workspace Setup — manages project workspace init and methodology bootstrap

**Portfolio Management** (`agents/portfolio-management/`)
- Demand Intake, Business Case, Portfolio Optimisation, Program Management

**Delivery Management** (`agents/delivery-management/`)
- Scope Definition, Lifecycle Governance, Schedule Planning, Resource Management, Financial Management, Vendor Procurement, Quality Management, Risk Management, Compliance Governance

**Operations Management** (`agents/operations-management/`)
- Change Control, Release Deployment, Knowledge Management, Continuous Improvement, Stakeholder Communications, Analytics Insights, Data Synchronisation, System Health

**Runtime** (`agents/runtime/src/`): Shared agent infrastructure — `base_agent.py` (BaseAgent class), `orchestrator.py`, `models.py`, `event_bus.py`, `state_store.py`, `memory_store.py`, `audit.py`, `policy.py`, `agent_catalog.py`

Each agent follows the pattern: `agents/<domain>/<agent-name>/src/<agent_module>.py` with corresponding tests, prompts, and README specs.

### Services (21 microservices under `services/`)

All services use FastAPI + Uvicorn. Standard structure: `src/`, `tests/`, `helm/`, `contracts/`, `Dockerfile`. `agent-config` and `memory_service` do not yet follow the full standard structure (missing `helm/`, `contracts/`, or `Dockerfile`). The `services/scope_baseline/` directory exists but is not a deployed microservice.

| Service | Port | Purpose |
|---------|------|---------|
| API Gateway | 8000 | Front door, auth, rate limiting, circuit breaker |
| Orchestration Service | 8080 | Multi-agent workflow coordination |
| Workflow Service | 8080 | Workflow execution, gate evaluation |
| Admin Console | 8080 | Platform operator management |
| Analytics Service | 8080 | KPI and metrics computation |
| Connector Hub | 8080 | Integration connector management |
| Document Service | 8080 | Document storage and versioning |
| Agent Runtime | 8080 | Agent hosting and connector integration |
| Agent Config | 8080 | Agent configuration CRUD |
| Audit Log | 8080 | Immutable audit trail (WORM) |
| Data Service | 8080 | Canonical schema/entity storage |
| Data Sync Service | 8080 | Connector-driven sync jobs |
| Data Lineage Service | 8080 | Lineage capture and quality scoring |
| Identity & Access | 8080 | SCIM + JWT token validation |
| Auth Service | 8080 | OAuth2/OIDC token exchange |
| Notification Service | 8080 | Email/chat/webhook delivery |
| Policy Engine | 8080 | RBAC/ABAC policy evaluation |
| Telemetry Service | 8080 | Metrics/events ingestion |
| Realtime Co-edit | 8080 | WebSocket collaborative editing |
| Memory Service | — | Conversation context persistence |

### Applications (under `apps/`)

| App | Tech Stack | Port |
|-----|-----------|------|
| Web Console | React 18 + Vite + FastAPI backend | 8501 |
| Mobile | React Native 0.73 + Expo 50 | — |
| Demo Streamlit | Streamlit | — |

### Shared packages (`packages/`)

- **common** — cross-cutting utilities
- **observability** — OpenTelemetry metrics, tracing, logging
- **security** — auth middleware, security headers, error handling
- **llm** — LLM provider abstraction, model registry, router
- **workflow** — workflow execution primitives
- **event-bus** — event messaging infrastructure
- **contracts** — API contract definitions
- **design-tokens** — UI design tokens (`@ppm/design-tokens`)
- **ui-kit** — React component library
- **feature-flags** — feature flag management
- **policy** — policy evaluation helpers
- **testing** — shared test utilities
- **crypto** — cryptographic primitives
- **data-quality** — data quality pipeline
- **methodology-engine** — project methodology (predictive/adaptive/hybrid)
- **canvas-engine** — canvas workspace engine
- **feedback** — feedback collection
- **vector_store** — vector store abstraction for knowledge search
- **connectors** — connector package helpers

### Connectors (`connectors/`)

40 connectors for external systems: Jira, Azure DevOps, Clarity, SAP, Workday, ServiceNow, Planview, Salesforce, Slack, Teams, SharePoint, M365, Confluence, Asana, Monday, SmartSheet, Google (Calendar, Drive), Oracle, NetSuite, Workday, ADP, Outlook, Zoom, Twilio, Logicgate, Archer, and more. Includes MCP (Model Context Protocol) variants for key integrations (Jira, Asana, Clarity, Planview, SAP, Slack, Teams, Workday).

- **SDK** (`connectors/sdk/`): Base classes (`base_connector.py`, `rest_connector.py`), auth, HTTP client, telemetry, sync controls
- **Registry** (`connectors/registry/`): Central `connectors.json`, JSON schemas for manifests/mappings
- **Mock connectors** (`connectors/mock/`): For testing without live services

### Data model (`data/`)

- **Schemas** (`data/schemas/`): 16 canonical JSON schemas — project, portfolio, program, resource, risk, budget, demand, vendor, work-item, document, issue, scenario, roi, agent-run, agent_config, audit-event
- **Migrations** (`data/migrations/versions/`): 9 Alembic migrations (0001–0009)
- **Quality rules** (`data/quality/rules.yaml`)
- **Lineage** (`data/lineage/`)

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | push to main/develop/claude/**, PRs | Full CI: lint, test (Python 3.11+3.12), security scans, Terraform validate, Helm lint, frontend tests, Docker image builds |
| `cd.yml` | post-CI on main | Continuous deployment to Azure |
| `pr.yml` | PRs | PR-specific checks |
| `release-gate.yml` | release | Release maturity gate |
| `e2e-tests.yml` | post-unit-tests | End-to-end test suite |
| `security-scan.yml` | scheduled | Trivy vulnerability scanning |
| `secret-scan.yml` | push | Gitleaks secret detection |
| `contract-tests.yml` | PRs | API contract enforcement |
| `performance-smoke.yml` | PRs | Performance regression checks |
| `container-scan.yml` | scheduled | Container vulnerability scanning |
| `connectors-live-smoke.yml` | scheduled + manual | Live smoke tests against real connector endpoints |
| `dast-staging.yml` | post-CD on staging | DAST (dynamic security) scan of deployed staging environment |
| `dependency-audit.yml` | weekly schedule | Dependency audit and compatibility checks |
| `iac-scan.yml` | PRs (infra paths) | Infrastructure-as-Code security scanning |
| `license-compliance.yml` | manual | License compliance check across all dependencies |
| `migration-check.yml` | manual | Database migration validation |
| `pr-labeler.yml` | PRs opened/updated | Automated PR label assignment |
| `promotion.yml` | manual | Environment promotion (staging → production) |
| `release.yml` | tags + manual | Full release workflow |
| `sbom.yml` | tag push | Software Bill of Materials generation |
| `static.yml` | push to main | Deploy static content (Storybook/docs) to GitHub Pages |
| `storybook-visual-regression.yml` | PRs (frontend paths) | Storybook visual regression testing |

CI test matrix: Python 3.11 and 3.12. Python 3.13 cross-platform (Ubuntu + Windows) compatibility job runs separately.

## Pre-commit hooks

Configured in `.pre-commit-config.yaml`:
- Ruff lint + format
- Prevent f-string interpolation in logger calls
- Placeholder/completeness quality gate

## Key file locations

| What | Where |
|------|-------|
| Python project config | `pyproject.toml` |
| Makefile targets | `Makefile` |
| CI/CD workflows | `.github/workflows/` |
| Environment template | `ops/config/.env.example` |
| Docker Compose | `ops/docker/docker-compose.yml` |
| Terraform | `ops/infra/terraform/` |
| K8s manifests | `ops/infra/kubernetes/manifests/` |
| Helm umbrella chart | `ops/infra/kubernetes/helm-charts/ppm-platform/` |
| Test conftest | `tests/conftest.py` |
| Agent catalog | `agents/AGENT_CATALOG.md` |
| Data schemas | `data/schemas/` |
| Connector registry | `connectors/registry/connectors.json` |
| RBAC config | `config/rbac/` |
| ABAC policies | `config/abac/` |
| Session start hook | `.claude/hooks/session-start.sh` |

## Testing details

- **Test root**: `tests/` (configured via `testpaths` in pyproject.toml)
- **Coverage minimum**: 80% (`--cov-fail-under=80`)
- **Async tests**: Use `@pytest.mark.asyncio`; fallback runner in conftest if pytest-asyncio unavailable
- **Fixtures**: `mock_azure_openai`, `mock_database`, `mock_redis`, `orchestrator`, `auth_headers` (JWT with test secret)
- **Path bootstrapping**: `tests/conftest.py` adds all monorepo `*/src` directories to `sys.path` with correct priority (api-gateway/src first)
- **Conditional collection**: Tests requiring optional dependencies (slowapi, celery, cryptography, azure, redis) are auto-skipped via `pytest_ignore_collect`
- **Environment variables for tests**: `AUTH_DEV_MODE=true`, `DATABASE_URL=sqlite+aiosqlite:///./test.db`, `REDIS_URL=redis://localhost:6379`

## Important conventions

1. **Never commit secrets** — use `.env` (gitignored) or Azure Key Vault. The `.gitleaks.toml` config and CI secret scanning enforce this.
2. **JSON Schemas are canonical** — all entity definitions in `data/schemas/` are the source of truth. Schema changes require migration version bumps.
3. **Connector maturity gates** — connectors must meet maturity thresholds checked by `make check-connector-maturity`.
4. **Docs migration guard** — legacy doc paths are blocked by `check-docs-migration-guard.py`.
5. **Generated docs must stay current** — `make check-generated-docs` enforces generated service/connector docs match source.
6. **API versioning** — all REST APIs are versioned under `/v1/`. Enforced by `check_api_versioning.py`.
7. **Health endpoints** — every service exposes `/healthz` (some also `/livez`, `/readyz`).
8. **Docker builds** — use multi-stage Docker BuildKit with `--from=repo-root` build context for monorepo dependencies. Non-root user (appuser:10001).
9. **Helm deployments** — each service has its own Helm chart; umbrella chart at `ops/infra/kubernetes/helm-charts/ppm-platform/`.
10. **Methodology support** — workspaces support predictive, adaptive, and hybrid project methodologies.
