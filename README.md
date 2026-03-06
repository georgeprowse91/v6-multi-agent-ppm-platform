# Multi-Agent PPM Platform

An AI-native Project Portfolio Management platform that deploys 25 specialized agents to orchestrate portfolio, program, and project delivery end to end. The platform combines a Python and TypeScript monorepo with FastAPI microservices, a React 18 web console, 40 integration connectors, and full Kubernetes deployment via Helm and Terraform, all targeting Microsoft Azure.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Table of Contents

- [Platform Overview](#platform-overview)
- [Key Capabilities](#key-capabilities)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Repository Structure](#repository-structure)
- [Agent System](#agent-system)
- [Microservices](#microservices)
- [Applications](#applications)
- [Connectors](#connectors)
- [Shared Packages](#shared-packages)
- [Data Model](#data-model)
- [Getting Started](#getting-started)
- [Running the Platform](#running-the-platform)
- [Testing](#testing)
- [Linting and Formatting](#linting-and-formatting)
- [Deployment](#deployment)
- [CI/CD Pipelines](#cicd-pipelines)
- [Security and Compliance](#security-and-compliance)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Platform Overview

The Multi-Agent PPM Platform is a production-ready system designed to bring AI-driven intelligence to every stage of project portfolio management. It provides a complete operating environment that includes:

- **25 domain-specialized AI agents** organized across four management domains, each backed by configurable LLM providers through Azure OpenAI.
- **16 microservices** handling concerns from identity and access control through to audit logging, telemetry, and real-time collaborative editing.
- **8 user-facing applications** including an API gateway, a React web console, a React Native mobile app, an admin console, and a Streamlit demo environment.
- **40 integration connectors** spanning project management tools, enterprise resource planning systems, communication platforms, and compliance software, with Model Context Protocol variants for key integrations.
- **20 shared packages** providing cross-cutting capabilities such as observability, security middleware, LLM abstraction, workflow primitives, and a React component library.
- **16 canonical JSON schemas** defining the data model for projects, portfolios, programs, resources, risks, budgets, and more.
- **Full infrastructure as code** with Terraform modules, Kubernetes manifests, Helm charts, and Docker multi-stage builds.

The platform supports predictive, adaptive, and hybrid project methodologies out of the box.

---

## Key Capabilities

- **Intelligent Routing** --- An intent router agent classifies user queries and dispatches them to the appropriate domain agents, with a response orchestration agent aggregating the results.
- **Portfolio Optimization** --- Demand intake, business case evaluation, and portfolio optimization agents work together to prioritize and balance the portfolio.
- **Full Delivery Lifecycle** --- Agents cover scope definition, schedule planning, resource management, financial management, vendor procurement, quality management, risk management, compliance governance, and lifecycle governance.
- **Operational Intelligence** --- Change control, release deployment, knowledge management, continuous improvement, stakeholder communications, analytics, data synchronization, and system health agents keep the platform and its projects running.
- **40 External Integrations** --- Out-of-the-box connectors for Jira, Azure DevOps, Clarity, SAP, Workday, ServiceNow, Salesforce, Slack, Microsoft Teams, SharePoint, Confluence, and many more.
- **Workspace Methodology Support** --- Workspaces can be configured as predictive (waterfall), adaptive (agile), or hybrid, with stage and gate structures adapting accordingly.
- **Enterprise Security** --- RBAC and ABAC policy enforcement, OAuth2/OIDC authentication, JWT validation, SCIM user provisioning, immutable audit trails, and secret scanning.
- **Observability** --- OpenTelemetry-based metrics, tracing, and logging with Grafana dashboard definitions and configurable alert thresholds.

---

## Architecture at a Glance

The platform follows a microservices architecture deployed on Kubernetes, with an event-driven backbone connecting agents, services, and connectors.

```
                          +------------------+
                          |   API Gateway    |  Port 8000
                          +--------+---------+
                                   |
                    +--------------+--------------+
                    |                             |
           +-------v--------+          +---------v-------+
           | Orchestration   |          |  Workflow        |
           | Service         |          |  Service         |
           +-------+--------+          +---------+-------+
                   |                              |
       +-----------+-----------+                  |
       |     Agent Runtime     |                  |
       |  (25 Domain Agents)   |                  |
       +-----------+-----------+                  |
                   |                              |
    +--------------+--------------+---------------+
    |              |              |               |
+---v---+   +-----v----+  +-----v-----+  +------v------+
| Data  |   | Identity |  | Policy    |  | Audit Log   |
|Service|   | & Access |  | Engine    |  |             |
+-------+   +----------+  +-----------+  +-------------+
```

All services expose a health endpoint at `/healthz`. REST APIs are versioned under `/v1/`. Inter-service communication uses an event bus backed by Azure Service Bus, with persistent state in Azure Cosmos DB and blob storage in Azure Blob Storage.

---

## Repository Structure

```
agents/                  25 domain agents organized by management domain, plus shared runtime
apps/                    User-facing applications (API gateway, web console, admin, mobile, and more)
config/                  RBAC and ABAC policy definitions
connectors/              40 integration connectors with SDK, registry, and MCP client
constraints/             Python version constraint files
data/                    Canonical JSON schemas, database migrations, quality rules, and lineage
docs/                    Architecture, methodology, agent catalog, onboarding, and runbooks
examples/                Scenario and configuration examples
integrations/            AI model, analytics, event bus, and persistence integration modules
ops/                     Docker Compose, Terraform, Kubernetes manifests, Helm charts, and scripts
packages/                Shared Python and TypeScript packages
services/                Backend microservices (audit, data, identity, notification, telemetry, and more)
tests/                   Unit, integration, end-to-end, security, contract, load, and performance tests
tools/                   Agent runner, connector runner, and local development tooling
vendor/                  Vendored stubs and third-party shims
```

---

## Agent System

The platform deploys 25 specialized agents across four management domains. Each agent lives under its own directory with dedicated source code, prompt templates, tests, and a specification README.

### Core Orchestration

| Agent | Purpose |
|-------|---------|
| Intent Router | Classifies user queries and routes them to the appropriate domain agents |
| Response Orchestration | Aggregates and synthesizes multi-agent responses into coherent outputs |
| Approval Workflow | Orchestrates approval chains, task inboxes, and escalation paths |
| Workspace Setup | Manages project workspace initialization and methodology bootstrapping |

### Portfolio Management

| Agent | Purpose |
|-------|---------|
| Demand Intake | Captures, categorizes, and deduplicates incoming project demands |
| Business Case | Evaluates business cases with financial modeling and strategic alignment scoring |
| Portfolio Optimisation | Optimizes portfolio composition against constraints, capacity, and strategic goals |
| Program Management | Coordinates cross-project dependencies and program-level governance |

### Delivery Management

| Agent | Purpose |
|-------|---------|
| Scope Definition | Defines project scope, generates WBS structures, and manages baseline traceability |
| Lifecycle Governance | Enforces stage-gate governance and lifecycle transition rules |
| Schedule Planning | Builds and maintains project schedules with dependency analysis |
| Resource Management | Allocates resources, detects conflicts, and forecasts capacity |
| Financial Management | Tracks budgets, forecasts costs, and manages earned value metrics |
| Vendor Procurement | Manages vendor evaluation, procurement workflows, and contract lifecycle |
| Quality Management | Defines quality criteria, manages inspections, and tracks defect resolution |
| Risk Management | Identifies, assesses, and monitors project risks with mitigation planning |
| Compliance Governance | Ensures regulatory compliance and manages audit evidence collection |

### Operations Management

| Agent | Purpose |
|-------|---------|
| Change Control | Manages change requests, impact assessment, and change advisory board workflows |
| Release Deployment | Coordinates release planning, deployment checklists, and rollback procedures |
| Knowledge Management | Captures lessons learned, maintains knowledge bases, and supports search |
| Continuous Improvement | Tracks improvement initiatives, retrospective actions, and maturity metrics |
| Stakeholder Communications | Generates status reports, stakeholder updates, and communication plans |
| Analytics Insights | Produces portfolio dashboards, trend analysis, and predictive analytics |
| Data Synchronisation | Orchestrates data sync between the platform and connected external systems |
| System Health | Monitors platform health, service dependencies, and operational readiness |

### Agent Runtime

All agents extend a shared runtime framework located in [agents/runtime/src](agents/runtime/src) that provides:

- **BaseAgent** --- Abstract base class with lifecycle hooks, LLM integration, and event emission
- **Orchestrator** --- Multi-agent coordination and parallel execution
- **Event Bus** --- Publish-subscribe messaging between agents and services
- **State Store** --- Persistent agent state management
- **Memory Store** --- Conversation context and session persistence
- **Policy Engine** --- Runtime policy evaluation for agent actions
- **Audit Logger** --- Immutable audit trail for all agent decisions

---

## Microservices

The platform comprises 16 backend microservices built with FastAPI and Uvicorn.

| Service | Port | Purpose |
|---------|------|---------|
| API Gateway | 8000 | Front door for all client requests with authentication, rate limiting, and circuit breaking |
| Orchestration Service | 8080 | Multi-agent workflow coordination and fan-out |
| Workflow Service | 8080 | Workflow persistence, execution, and gate evaluation |
| Agent Runtime | 8080 | Agent hosting, lifecycle management, and connector integration |
| Agent Config | 8080 | Agent configuration CRUD operations |
| Audit Log | 8080 | Immutable write-once-read-many audit trail with retention enforcement |
| Auth Service | 8080 | OAuth2 and OIDC token exchange |
| Data Service | 8080 | Canonical schema and entity storage |
| Data Sync Service | 8080 | Connector-driven synchronization jobs and conflict management |
| Data Lineage Service | 8080 | Data lineage capture and quality scoring |
| Identity and Access | 8080 | SCIM user provisioning and JWT token validation |
| Notification Service | 8080 | Email, chat, and webhook notification delivery |
| Policy Engine | 8080 | RBAC and ABAC policy evaluation |
| Telemetry Service | 8080 | Metrics and event ingestion for observability |
| Realtime Co-edit | 8080 | WebSocket-based collaborative editing |
| Memory Service | --- | Conversation context persistence |

The API Gateway, Orchestration Service, and Workflow Service are located under [apps](apps) rather than [services](services). All other services live under their respective directories in [services](services).

---

## Applications

| Application | Technology | Port | Purpose |
|-------------|-----------|------|---------|
| API Gateway | FastAPI | 8000 | Authentication, routing, rate limiting, and circuit breaking |
| Web Console | React 18, Vite, FastAPI backend | 8501 | Primary user interface for portfolio and project management |
| Mobile | React Native 0.73, Expo 50 | --- | Mobile companion application |
| Admin Console | FastAPI | 8080 | Platform administration and configuration |
| Analytics Service | FastAPI | 8080 | Portfolio analytics and reporting |
| Document Service | FastAPI | 8080 | Document management and generation |
| Connector Hub | FastAPI | 8080 | Connector management and monitoring |
| Demo (Streamlit) | Streamlit | --- | Standalone demonstration environment with bundled sample data |

---

## Connectors

The platform includes 40 integration connectors for external systems, each with a manifest, field mappings, and authentication configuration. Connectors are built on a shared SDK that provides base classes, HTTP client utilities, authentication handlers, telemetry hooks, and sync controls.

### Project and Work Management

Jira, Azure DevOps, Clarity, Planview, Asana, Monday.com, SmartSheet, Microsoft Project Server

### Enterprise Resource Planning

SAP, Oracle, NetSuite, Workday, SAP SuccessFactors, ADP

### Communication and Collaboration

Slack, Microsoft Teams, Zoom, Twilio, Outlook, Microsoft 365, SharePoint, Confluence, Google Calendar, Google Drive

### CRM and Service Management

Salesforce, ServiceNow

### Governance, Risk, and Compliance

Archer, LogicGate, Regulatory Compliance

### Specialized

Azure Communication Services, Azure DevOps, IoT, Notification Hubs

### Model Context Protocol Variants

MCP-enabled connectors are available for Jira, Asana, Clarity, Planview, SAP, Slack, Teams, and Workday, providing structured tool-use interfaces for LLM-driven agent interactions.

The connector registry, manifests, and JSON schemas are maintained in [connectors/registry](connectors/registry).

---

## Shared Packages

The [packages](packages) directory contains shared libraries consumed by agents, services, and applications.

| Package | Description |
|---------|-------------|
| common | Cross-cutting utilities used throughout the platform |
| observability | OpenTelemetry metrics, distributed tracing, and structured logging |
| security | Authentication middleware, security headers, and error handling |
| llm | LLM provider abstraction, model registry, and routing |
| workflow | Workflow execution primitives and step definitions |
| event-bus | Event messaging infrastructure |
| contracts | API contract definitions |
| design-tokens | UI design tokens published as `@ppm/design-tokens` |
| ui-kit | React component library |
| feature-flags | Feature flag management |
| policy | Policy evaluation helpers |
| testing | Shared test utilities and fixtures |
| crypto | Cryptographic primitives |
| data-quality | Data quality pipeline and rule evaluation |
| methodology-engine | Project methodology support for predictive, adaptive, and hybrid approaches |
| canvas-engine | Canvas workspace engine |
| feedback | Feedback collection and prompt flagging |
| vector_store | Vector store abstraction for knowledge search |
| connectors | Connector package helpers |

---

## Data Model

The canonical data model is defined by 16 JSON schemas in [data/schemas](data/schemas). These schemas are the single source of truth for all entity definitions across the platform.

| Schema | Description |
|--------|-------------|
| project | Project definition with metadata, lifecycle, and methodology |
| portfolio | Portfolio container with strategic alignment and scoring |
| program | Program grouping with cross-project dependency tracking |
| resource | Resource profiles, skills, availability, and allocation |
| risk | Risk register entries with probability, impact, and mitigation |
| budget | Budget line items, forecasts, and actuals |
| demand | Demand intake records with categorization and prioritization |
| vendor | Vendor profiles, evaluations, and contract details |
| work-item | Individual work items, tasks, and deliverables |
| document | Document metadata, versioning, and storage references |
| issue | Issue tracking with severity, assignment, and resolution |
| scenario | What-if scenario definitions for portfolio optimization |
| roi | Return on investment calculations and projections |
| agent-run | Agent execution records with inputs, outputs, and timing |
| agent_config | Agent configuration including model, prompt, and policy settings |
| audit-event | Immutable audit event records |

Database migrations are managed with Alembic under [data/migrations](data/migrations).

---

## Getting Started

### Prerequisites

- Python 3.11 or later (tested on 3.11, 3.12, and 3.13)
- Node.js and pnpm (for frontend packages)
- Docker and Docker Compose (for the local development stack)

### Installation

```bash
make install-dev
```

This installs all development and test dependencies and sets up pre-commit hooks.

### Environment Configuration

```bash
cp ops/config/.env.example .env
```

Edit the `.env` file with your credentials. The example file contains development-only defaults that must never be used in staging or production environments. Secrets should be sourced from Azure Key Vault in deployed environments.

---

## Running the Platform

### Full Local Stack

Start all core services with Docker Compose:

```bash
make dev-up
```

### Individual Components

```bash
make run-api              # API gateway at http://localhost:8000
make run-web              # Web console at http://localhost:8501
```

### Demo Mode

For a full-functionality demonstration environment with interactive scenarios:

```bash
# Set DEMO_MODE=true in your .env file
make dev-up
```

### Standalone Streamlit Demo

Run a fully local demo with bundled sample data, requiring no Docker or backend services:

```bash
python -m venv venv
source venv/bin/activate
pip install -r ops/requirements/requirements-demo.txt
streamlit run apps/demo_streamlit/app.py
```

### Expected Endpoints

| Endpoint | URL |
|----------|-----|
| API Gateway | http://localhost:8000 |
| API Documentation | http://localhost:8000/v1/docs |
| Web Console | http://localhost:8501 |

---

## Testing

The test suite is organized into multiple categories under the [tests](tests) directory.

```bash
make test-unit            # Unit tests only
make test-integration     # Integration tests
make test-e2e             # End-to-end tests
make test-security        # Security tests
make test-all             # Full suite (unit + integration + e2e + security)
make test-cov             # Full suite with coverage enforcement (minimum 80%)
```

Tests are configured in `pyproject.toml` with a 60-second default timeout per test. Async tests use `@pytest.mark.asyncio`. The test conftest at [tests/conftest.py](tests/conftest.py) bootstraps `sys.path` so that all monorepo packages are importable.

### Quality Gates

```bash
make check                # Lint + test + doc scans
make ci-local             # Full CI check battery
make release-gate PROFILE=core   # Release maturity gate
```

---

## Linting and Formatting

```bash
make lint                 # Ruff + Black + MyPy
make format               # Auto-format with Black + Ruff
```

**Python standards:** Black (line length 100, targeting Python 3.11), Ruff (rules E, F, I, N, W, UP, G), and MyPy with strict settings. Google-style docstrings. Parameterized logging enforced by pre-commit hooks.

**TypeScript standards:** ESLint, with Vitest for testing and pnpm as the package manager.

---

## Deployment

### Infrastructure as Code

Terraform modules for Azure infrastructure are in [ops/infra/terraform](ops/infra/terraform):

```bash
make tf-init
make tf-plan
make tf-apply
```

### Kubernetes

- Manifests: [ops/infra/kubernetes/manifests](ops/infra/kubernetes/manifests)
- Helm charts: Each service has its own chart; the umbrella chart is at [ops/infra/kubernetes/helm-charts/ppm-platform](ops/infra/kubernetes/helm-charts/ppm-platform)

### Observability Stack

Deploy the OpenTelemetry collector via the dedicated Helm chart:

```bash
helm upgrade --install ppm-observability \
  ops/infra/kubernetes/helm-charts/observability \
  --namespace observability \
  --create-namespace
```

### Docker

All services use multi-stage Docker builds with BuildKit. Containers run as a non-root user (appuser, UID 10001). The Docker Compose configuration is at [ops/docker/docker-compose.yml](ops/docker/docker-compose.yml).

---

## CI/CD Pipelines

GitHub Actions workflows are defined in [.github/workflows](.github/workflows). The CI test matrix covers Python 3.11 and 3.12, with a separate cross-platform compatibility job for Python 3.13 on Ubuntu and Windows.

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| CI | Push to main, develop, or claude branches; pull requests | Lint, test, security scan, Terraform validate, Helm lint, frontend tests, Docker builds |
| CD | After CI passes on main | Continuous deployment to Azure |
| PR Checks | Pull requests | PR-specific validation |
| Release Gate | Release events | Release maturity verification |
| End-to-End Tests | After unit tests pass | Full end-to-end test suite |
| Security Scan | Scheduled | Trivy vulnerability scanning |
| Secret Scan | Every push | Gitleaks secret detection |
| Contract Tests | Pull requests | API contract enforcement |
| Performance Smoke | Pull requests | Performance regression checks |
| Container Scan | Scheduled | Container image vulnerability scanning |
| Connector Smoke | Scheduled and manual | Live smoke tests against real connector endpoints |
| DAST Staging | After CD on staging | Dynamic application security testing |
| Dependency Audit | Weekly | Dependency audit and compatibility checks |
| IAC Scan | Pull requests touching infrastructure | Infrastructure-as-code security scanning |
| License Compliance | Manual | License compliance check across all dependencies |
| Migration Check | Manual | Database migration validation |
| PR Labeler | Pull request events | Automated PR label assignment |
| Promotion | Manual | Environment promotion from staging to production |
| Release | Tags and manual | Full release workflow |
| SBOM | Tag push | Software Bill of Materials generation |
| Static Deploy | Push to main | Deploy Storybook and docs to GitHub Pages |
| Visual Regression | Pull requests touching frontend | Storybook visual regression testing |

---

## Security and Compliance

- **Authentication:** OAuth2 and OIDC token exchange via the Auth Service, with JWT validation at the API Gateway.
- **Authorization:** RBAC and ABAC policies defined in [config/rbac](config/rbac) and [config/abac](config/abac), evaluated by the Policy Engine service.
- **User Provisioning:** SCIM 2.0 support in the Identity and Access service.
- **Audit Trail:** Immutable write-once-read-many audit log with retention enforcement.
- **Secret Management:** Azure Key Vault integration. Gitleaks scanning enforced in CI. No secrets committed to the repository.
- **Security Architecture:** Documented in [docs/architecture/security-architecture.md](docs/architecture/security-architecture.md).
- **Responsible Disclosure:** See [SECURITY.md](SECURITY.md).

---

## Documentation

Comprehensive documentation is maintained in the [docs](docs) directory.

| Topic | Location |
|-------|----------|
| Documentation Hub | [docs/README.md](docs/README.md) |
| Architecture Overview | [docs/architecture/README.md](docs/architecture/README.md) |
| Architecture Decision Records | [docs/architecture/adr](docs/architecture/adr) |
| Agent Catalog | [agents/AGENT_CATALOG.md](agents/AGENT_CATALOG.md) |
| Agent Documentation | [docs/agents.md](docs/agents.md) |
| Connector Overview | [docs/connectors](docs/connectors) |
| Data Model and Lineage | [docs/data.md](docs/data.md) |
| Methodology Guide | [docs/methodology](docs/methodology) |
| Developer Onboarding | [docs/onboarding/developer-onboarding.md](docs/onboarding/developer-onboarding.md) |
| Demo Environment Setup | [docs/demo-environment.md](docs/demo-environment.md) |
| Quickstart Runbook | [docs/runbooks/quickstart.md](docs/runbooks/quickstart.md) |
| Operational Runbooks | [docs/runbooks](docs/runbooks) |
| Production Readiness | [docs/production-readiness](docs/production-readiness) |
| Platform User Guide | [docs/platform-userguide.md](docs/platform-userguide.md) |
| Solution Overview | [docs/platform-description.md](docs/platform-description.md) |
| Versioning Strategy | [docs/versioning.md](docs/versioning.md) |
| Change Management | [docs/change-management.md](docs/change-management.md) |
| Design System | [docs/design-system.md](docs/design-system.md) |
| Disaster Recovery Runbook | [docs/dr-runbook.md](docs/dr-runbook.md) |

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on code style, branch naming, commit messages, and the pull request process.

### Commit Message Format

Use conventional commits: `<type>: <subject>`

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Branch Naming

Prefix branches with: `feature/`, `fix/`, `docs/`, `refactor/`, `test/`

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
