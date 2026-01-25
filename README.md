# Multi-Agent PPM Platform

AI-native Project Portfolio Management platform with 25 specialized agents orchestrating portfolio, program, and project delivery.

[![CI/CD](https://github.com/your-org/multi-agent-ppm-platform/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/your-org/multi-agent-ppm-platform/actions)
[![codecov](https://codecov.io/gh/your-org/multi-agent-ppm-platform/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/multi-agent-ppm-platform)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

The Multi-Agent PPM Platform is an enterprise-grade, AI-native solution that transforms how organizations manage their project portfolios. It combines 25 specialized AI agents with proven PPM methodologies (Agile, Waterfall, Hybrid) to provide intelligent orchestration, real-time insights, and automated workflows.

**Implementation Status (Alpha):**
- Core API scaffolding and agent orchestration runtime are implemented.
- Agent logic is currently mocked/stubbed to keep the system runnable while specs are finalized.
- Integrations, persistence, and production auth are documented but not yet wired in.

**Key Features:**
- 🤖 25 specialized AI agents for different PPM domains
- 🔄 Multi-methodology support (Agile, Waterfall, Hybrid)
- 🔌 Extensive integrations (Jira, SAP, Workday, Slack, Teams, etc.)
- 📊 Advanced analytics and predictive insights
- 🔐 Enterprise-grade security and compliance
- ☁️ Cloud-native Azure architecture

## 📚 Documentation

- **[Solution Overview](docs/product/solution-overview.md)** - Product vision and value proposition
- **[Architecture Documentation](docs/architecture/)** - System design and technical architecture
- **[Agent Specifications](agents/README.md)** - Detailed specs for all 25 agents
- **[Product Requirements](docs/product/)** - Functional and non-functional requirements
- **[Integration Guides](docs/connectors/)** - Connector specifications
- **[API Documentation](http://localhost:8000/api/docs)** - Interactive API docs (when running)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Azure subscription (for cloud deployment)
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/multi-agent-ppm-platform.git
cd multi-agent-ppm-platform
```

### 2. Quick Start (Recommended for First-Time Users)

```bash
make quick-start
```

This will:
- Copy `.env.example` to `.env`
- Install dependencies
- Start all services in Docker

Services will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Web Prototype**: http://localhost:8501
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### 3. Configure Environment

Edit `.env` with your Azure credentials:

```bash
# Azure OpenAI (required for AI agents)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Database (auto-configured for Docker)
DATABASE_URL=postgresql://ppm:ppm_password@localhost:5432/ppm
REDIS_URL=redis://localhost:6379/0
```

See [`.env.example`](.env.example) for all configuration options.

### Troubleshooting (Top 3)

1. **`docker: No such file or directory` or Docker daemon not running**
   - Install Docker Desktop (or Docker Engine + Compose) and ensure the daemon is running.
   - Re-run: `make docker-up` or `make quick-start`.
2. **`pytest: error: unrecognized arguments: --cov...`**
   - You’re missing dev dependencies. Install them with `make install-dev` (or `pip install -e .[dev]`),
     then re-run `make test`.
3. **`Address already in use` when starting the API or web prototype**
   - Stop the conflicting process or change ports:
     - API: `uvicorn api.main:app --port 8001 --app-dir apps/api-gateway/src`
     - Prototype: `streamlit run apps/web/streamlit_app.py --server.port 8502`

## 🛠️ Development

### Install Dependencies

```bash
# Production dependencies
make install

# Development dependencies (recommended)
make install-dev

# Alternative dev install without editable package mode
pip install -r requirements-dev.txt
```

### Run Services

#### Option 1: Docker Compose (Recommended)

```bash
# Start all services
make docker-up

# Start in detached mode
make docker-up-d

# View logs
make docker-logs

# Stop services
make docker-down
```

#### Option 2: Local Development

```bash
# Terminal 1: Run API
make run-api

# Terminal 2: Run web prototype
make run-prototype
```

### Verify the API is running

```bash
curl http://localhost:8000/healthz
```

Expected response:

```json
{"status":"ok","timestamp":"2024-01-01T12:00:00","version":"0.1.0"}
```

```bash
curl http://localhost:8000/version
```

Expected response:

```json
{"service":"multi-agent-ppm-api","version":"0.1.0","build_sha":"unknown"}
```

### Security Notes (Production Hardening)

- The API CORS policy defaults to local origins for development. Set `ALLOWED_ORIGINS` in `.env` for
  production deployments (no wildcards). See [`.env.example`](.env.example) for format.

### Testing

```bash
# Run all tests with coverage
make test

# Quick tests (no coverage)
make test-quick

# Run specific test file
pytest tests/test_intent_router.py

# Run linters
make lint

# Format code
make format

# Run all checks
make check
```

> Note: Test execution requires development dependencies (pytest-asyncio, pytest-cov). Install them via
> `make install-dev` or `pip install -r requirements-dev.txt`.

## 📦 Building & Deployment

### Build Docker Images

```bash
# Build production API image
make docker-build

# Build web image
make docker-build-prototype
```

### Deploy to Azure

#### 1. Provision Infrastructure with Terraform

```bash
# Initialize Terraform
make tf-init

# Plan infrastructure
make tf-plan

# Apply infrastructure
make tf-apply
```

See [infra/README.md](infra/README.md) for detailed deployment instructions.

#### 2. Deploy to Kubernetes

```bash
# Configure secrets
cp infra/kubernetes/secrets.yaml.example infra/kubernetes/secrets.yaml
# Edit secrets.yaml with your values

# Deploy
make k8s-deploy

# Check status
make k8s-status

# View logs
make k8s-logs
```

### CI/CD Pipeline

The platform includes automated CI/CD workflows:

- **Linting & Testing**: On every push and PR
- **Docker Build**: On successful tests
- **Security Scanning**: Trivy vulnerability scanning
- **Auto-Deploy**: To dev environment on merge to main

See [.github/workflows/ci.yml](.github/workflows/ci.yml) for details.

## 🏗️ Project Structure

```
multi-agent-ppm-platform/
├── apps/                  # Deployable apps (API gateway, web)
├── agents/                # Agent implementations + runtime SDK
├── connectors/            # Connector implementations
├── packages/              # Shared libraries
├── services/              # Supporting backend services
├── docs/                  # Product, architecture, and ops docs
├── config/                # Environment and RBAC config
├── infra/                 # IaC and deployment assets
├── tests/                 # Test suite
└── tools/                 # Dev tooling and helpers
```

## 🤖 Agents

The platform includes 25 specialized agents organized by domain:

### Core Orchestration (2)
- **Agent 1**: Intent Router - NLP-based query routing
- **Agent 2**: Response Orchestration - Multi-agent coordination

### Portfolio Management (4)
- **Agent 4**: Demand & Intake - Multi-channel request capture
- **Agent 5**: Business Case & Investment Analysis
- **Agent 6**: Portfolio Strategy & Optimization
- **Agent 7**: Program Management

### Delivery (6)
- **Agent 8**: Project Definition & Scope
- **Agent 9**: Project Lifecycle & Governance
- **Agent 10**: Schedule & Planning
- **Agent 11**: Resource & Capacity Management
- **Agent 12**: Financial Management
- **Agent 13**: Vendor & Procurement

### Governance (4)
- **Agent 14**: Quality Assurance & Testing
- **Agent 15**: Risk & Issue Management
- **Agent 16**: Compliance & Security
- **Agent 17**: Change & Configuration Management

### Operations (4)
- **Agent 18**: Release & Deployment
- **Agent 19**: Knowledge & Document Management
- **Agent 20**: Continuous Improvement
- **Agent 21**: Stakeholder & Communications

### Platform (4)
- **Agent 22**: Analytics & Insights
- **Agent 23**: Data Synchronization & Quality
- **Agent 24**: Workflow & Process Engine
- **Agent 25**: System Health & Monitoring

### Support (1)
- **Agent 3**: Approval Workflow

See [agents/README.md](agents/README.md) for detailed specifications.

## 🔌 Integrations

Connectors for enterprise systems:

- **Project Management**: Jira, Azure DevOps, Planview, Monday.com
- **Financial**: SAP, Workday, Oracle, NetSuite
- **Collaboration**: Slack, Microsoft Teams
- **Documents**: SharePoint, Confluence, Google Drive
- **CRM**: Salesforce, ServiceNow
- **Identity**: Azure AD, Okta

See [Connector Specifications](docs/connectors/overview.md).

## 📖 Additional Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture overview
- **[Docs Hub](docs/README.md)** - Product, architecture, runbooks, and compliance
- **[API Reference](http://localhost:8000/api/docs)** - Interactive API documentation

## 🧪 Testing

```bash
# Run full test suite
pytest

# With coverage report
pytest --cov=agents --cov=apps --cov=packages --cov=tools --cov-report=html

# View coverage
open htmlcov/index.html
```

Current coverage: **reported in CI** (target: >80%)

## 🛡️ Security

- Azure AD integration for authentication
- RBAC for fine-grained access control
- Secrets managed in Azure Key Vault
- All data encrypted at rest and in transit
- SOC 2 / ISO 27001 compliance ready

See [Security Architecture](docs/architecture/security-architecture.md).
See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## 📊 Monitoring & Observability

- Application Insights for telemetry
- Azure Monitor for infrastructure metrics
- Distributed tracing with OpenTelemetry
- Custom dashboards for agent performance

See [Observability & Monitoring](docs/architecture/observability-architecture.md).

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/multi-agent-ppm-platform/issues)
- **Documentation**: [docs/](docs/)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/multi-agent-ppm-platform/discussions)

## 🗺️ Roadmap

See [Implementation Roadmap](docs/product/success-metrics.md) for the full development plan.

**Current Status**: v0.1.0 - Alpha
- ✅ Core orchestration agents implemented
- ✅ Production infrastructure scaffolding
- ✅ CI/CD pipeline
- 🚧 Agent implementations in progress
- 🚧 Connector integrations in progress
- 📅 Beta release: Q2 2026

## 📝 Citation

If you use this platform in your research or work, please cite:

```bibtex
@software{multi_agent_ppm_platform,
  title = {Multi-Agent PPM Platform},
  author = {Your Organization},
  year = {2026},
  url = {https://github.com/your-org/multi-agent-ppm-platform}
}
```

---

**Made with ❤️ by the Multi-Agent PPM Team**
