# Architecture Overview

This document provides a high-level overview of the Multi-Agent PPM Platform architecture. For detailed technical specifications, see the [comprehensive architecture documentation](docs/architecture/).

## Table of Contents

- [System Overview](#system-overview)
- [Core Principles](#core-principles)
- [Architecture Diagram](#architecture-diagram)
- [Component Overview](#component-overview)
- [Agent Architecture](#agent-architecture)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Security Architecture](#security-architecture)
- [Deployment Architecture](#deployment-architecture)
- [Integration Patterns](#integration-patterns)

## System Overview

The Multi-Agent PPM Platform is a cloud-native, event-driven system built on Microsoft Azure. It uses a **multi-agent architecture** where 25 specialized AI agents coordinate to deliver comprehensive PPM capabilities.

### Key Characteristics

- **Cloud-Native**: Built for Azure with containerized microservices
- **Event-Driven**: Asynchronous communication via Azure Service Bus
- **AI-Powered**: Azure OpenAI for intelligent decision-making
- **Multi-Methodology**: Supports Agile, Waterfall, and Hybrid approaches
- **Highly Scalable**: Horizontal scaling with Kubernetes
- **Secure**: Enterprise-grade security and compliance

## Core Principles

### 1. Agent-Based Architecture

Each domain (portfolio, delivery, governance, etc.) is managed by specialized agents that:
- Operate autonomously within their domain
- Communicate via standard interfaces
- Can be developed and deployed independently
- Scale based on demand

### 2. Human-in-the-Loop

AI agents provide recommendations and automation, but humans make final decisions on:
- Portfolio prioritization
- Budget approvals
- Risk acceptance
- Scope changes

### 3. Methodology Agnostic

The platform adapts to the project methodology:
- **Agile**: Sprint planning, burndown charts, velocity tracking
- **Waterfall**: Phase gates, Gantt charts, earned value management
- **Hybrid**: Mixed approach based on project needs

### 4. Integration-First

Built to integrate with existing enterprise systems rather than replace them:
- Planview, Jira, Azure DevOps for project management
- SAP, Workday for financials
- Slack, Teams for collaboration

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          Users                                   │
│  (Executives, PMO, Project Managers, Team Members)              │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Presentation Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Web UI      │  │  Mobile UI   │  │  API Clients │          │
│  │  (React)     │  │  (Future)    │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway                                 │
│              (Azure API Management)                              │
│   Authentication, Rate Limiting, Routing, Monitoring            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Core Orchestration Layer                        │
│  ┌──────────────────────┐  ┌──────────────────────────┐        │
│  │  Intent Router       │──│  Response Orchestration   │        │
│  │  Agent 1             │  │  Agent 2                  │        │
│  └──────────────────────┘  └──────────────────────────┘        │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Portfolio   │ │  Delivery    │ │  Governance  │ │  Platform    │
│  Agents      │ │  Agents      │ │  Agents      │ │  Agents      │
│  (4-7)       │ │  (8-13)      │ │  (14-17)     │ │  (22-25)     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │                │
       └────────────────┴────────────────┴────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PostgreSQL  │  │  Cosmos DB   │  │  Redis       │          │
│  │  (Relational)│  │  (Documents) │  │  (Cache)     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Integration Layer                               │
│  External Systems: Jira, SAP, Workday, Slack, Teams, etc.      │
└─────────────────────────────────────────────────────────────────┘
```

## Component Overview

### Core Orchestration Agents

**Intent Router (Agent 1)**
- Receives user queries
- Classifies intent using NLP
- Routes to appropriate domain agents

**Response Orchestration (Agent 2)**
- Coordinates multi-agent workflows
- Manages parallel/sequential execution
- Aggregates responses

**Approval Workflow (Agent 3)**
- Routes approvals to appropriate stakeholders
- Tracks approval status
- Enforces governance policies

### Domain Agents

#### Portfolio Management (Agents 4-7)
- Demand & Intake
- Business Case & Investment Analysis
- Portfolio Strategy & Optimization
- Program Management

#### Delivery (Agents 8-13)
- Project Definition & Scope
- Project Lifecycle & Governance
- Schedule & Planning
- Resource & Capacity Management
- Financial Management
- Vendor & Procurement

#### Governance (Agents 14-17)
- Quality Assurance & Testing
- Risk & Issue Management
- Compliance & Security
- Change & Configuration Management

#### Operations (Agents 18-21)
- Release & Deployment
- Knowledge & Document Management
- Continuous Improvement
- Stakeholder & Communications

#### Platform (Agents 22-25)
- Analytics & Insights
- Data Synchronization & Quality
- Workflow & Process Engine
- System Health & Monitoring

## Agent Architecture

### Base Agent Pattern

All agents inherit from `BaseAgent` which provides:

```python
class BaseAgent(ABC):
    - initialize()      # Setup resources
    - validate_input()  # Validate requests
    - process()         # Core logic (abstract)
    - execute()         # Full workflow with error handling
    - cleanup()         # Resource cleanup
```

### Agent Communication

Agents communicate via:

1. **Synchronous**: Direct HTTP/REST calls for immediate responses
2. **Asynchronous**: Azure Service Bus for event-driven workflows
3. **Data Sharing**: Shared data layer (PostgreSQL, Cosmos DB)

### Agent Lifecycle

```
Initialize → Validate → Process → Respond → Cleanup
     ↓          ↓          ↓         ↓         ↓
  Resources   Input      Logic    Output    Release
   (DB, AI)   Check     Execute   Format   Resources
```

## Data Flow

### Query Processing Flow

```
1. User Query
   ↓
2. API Gateway (Authentication, Rate Limiting)
   ↓
3. Intent Router Agent (Classify Intent)
   ↓
4. Response Orchestration Agent (Plan Execution)
   ↓
5. Domain Agents (Parallel/Sequential Execution)
   ↓
6. Response Aggregation (Synthesize Results)
   ↓
7. User Response
```

### Event-Driven Flow

```
1. Event Occurs (e.g., project created)
   ↓
2. Event Published to Service Bus
   ↓
3. Subscribed Agents Notified
   ↓
4. Agents Process Event Asynchronously
   ↓
5. Results Stored / Notifications Sent
```

## Technology Stack

### Backend

- **Language**: Python 3.11+
- **Framework**: FastAPI (async REST API)
- **AI/ML**: Azure OpenAI, LangChain
- **Task Queue**: Azure Service Bus
- **Caching**: Redis

### Data Storage

- **Relational**: PostgreSQL 15 (transactional data)
- **Document**: Azure Cosmos DB (flexible schemas)
- **Cache**: Azure Cache for Redis
- **Object Storage**: Azure Blob Storage (documents, files)
- **Search**: Azure Cognitive Search (semantic search)

### Infrastructure

- **Cloud Provider**: Microsoft Azure
- **Container Orchestration**: Azure Kubernetes Service (AKS)
- **Container Registry**: Azure Container Registry
- **IaC**: Terraform
- **CI/CD**: GitHub Actions

### AI Services

- **Language Models**: Azure OpenAI (GPT-4)
- **NLP**: Azure Cognitive Services
- **ML Training**: Azure Machine Learning

### Frontend (Prototype)

- **Framework**: Streamlit (prototype)
- **Planned**: React with TypeScript

## Security Architecture

### Authentication & Authorization

- **Identity Provider**: Azure Active Directory (Entra ID)
- **API Security**: OAuth 2.0 / OIDC
- **RBAC**: Role-based access control at API and data levels

### Data Security

- **Encryption at Rest**: Azure Storage Service Encryption (SSE)
- **Encryption in Transit**: TLS 1.3
- **Secrets Management**: Azure Key Vault
- **Network Security**: Virtual Networks, Private Endpoints

### Compliance

- **Standards**: SOC 2, ISO 27001, GDPR
- **Audit Logging**: Azure Monitor, Application Insights
- **Data Classification**: Sensitive data tagging and access controls

See [Security Architecture](docs/architecture/security-architecture.md) for details.

## Deployment Architecture

### Azure Resources

```
Resource Group
├── AKS Cluster (Container orchestration)
├── Container Registry (Docker images)
├── PostgreSQL Flexible Server (Primary database)
├── Cosmos DB Account (Document storage)
├── Redis Cache (Caching layer)
├── Azure OpenAI (AI services)
├── Key Vault (Secrets management)
├── Service Bus Namespace (Event messaging)
├── Storage Account (Data Lake Gen2)
├── Application Insights (Monitoring)
└── API Management (API gateway)
```

### Deployment Environments

- **Development**: Single region, basic SKUs
- **Staging**: Production-like, reduced capacity
- **Production**: Multi-region, premium SKUs, geo-redundancy

### Scaling Strategy

- **Horizontal Scaling**: Kubernetes HPA based on CPU/memory
- **Vertical Scaling**: Azure resource tier adjustments
- **Auto-Scaling Rules**:
  - Scale out at 70% CPU utilization
  - Scale in at 30% CPU utilization
  - Min replicas: 2, Max replicas: 10

## Integration Patterns

### Inbound Integration

External systems → Platform via:
1. **REST APIs**: Synchronous requests
2. **Webhooks**: Event notifications
3. **Message Queue**: Azure Service Bus

### Outbound Integration

Platform → External systems via:
1. **Connectors**: Adapter pattern for each system
2. **API Calls**: REST/GraphQL to external APIs
3. **Events**: Publish to Service Bus for async processing

### Integration Security

- OAuth 2.0 for authentication
- API keys stored in Key Vault
- Rate limiting and retry policies
- Circuit breakers for fault tolerance

See [Integration Architecture](docs/architecture/connector-architecture.md) for connector specifications.

## Performance Considerations

### Caching Strategy

- **Agent Responses**: Cache frequent queries (15 min TTL)
- **Static Data**: Cache reference data (1 hour TTL)
- **Session Data**: Redis for user sessions

### Database Optimization

- **Connection Pooling**: Reuse database connections
- **Indexing**: Index frequently queried fields
- **Read Replicas**: Separate read/write workloads

### API Performance

- **Async I/O**: Non-blocking operations
- **Response Compression**: Gzip compression
- **Pagination**: Limit large result sets

## Monitoring & Observability

- **Application Insights**: Telemetry and traces
- **Azure Monitor**: Infrastructure metrics
- **Custom Dashboards**: Agent performance metrics
- **Alerting**: Proactive issue detection

See [Observability & Monitoring](docs/architecture/observability-architecture.md).

## Further Reading

- **[Detailed Architecture](docs/architecture/README.md)** - In-depth technical specifications
- **[Data Architecture](docs/architecture/data-architecture.md)** - Data models and flows
- **[Deployment Architecture](docs/architecture/deployment-architecture.md)** - Deployment and infrastructure
- **[Agent Specifications](agents/README.md)** - Individual agent details
- **[API Documentation](http://localhost:8000/api/docs)** - Interactive API reference

---

For questions or clarifications, see [CONTRIBUTING.md](CONTRIBUTING.md) or open an [issue](https://github.com/your-org/multi-agent-ppm-platform/issues).
