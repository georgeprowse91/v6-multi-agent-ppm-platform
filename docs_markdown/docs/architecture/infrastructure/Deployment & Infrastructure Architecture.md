# Deployment & Infrastructure Architecture

## Overview

This document describes the deployment and infrastructure architecture for the multi‑agent Project Portfolio Management (PPM) platform. The goal is to provide a flexible yet secure foundation that supports software‑as‑a‑service (SaaS), private cloud and on‑premises deployments. It covers hosting models, the microservices layout, scaling strategies and the continuous integration/continuous deployment (CI/CD) pipeline necessary to operate the solution across different client environments.

The platform is composed of ~25 specialised AI agents orchestrated through a central orchestration layer, a set of connectors that integrate with external systems, a data platform and a user interface. Each agent is containerised and deployed independently, allowing teams to scale, update and manage them without disrupting the entire system. The infrastructure design emphasises scalability, resilience, security and compliance with Australian frameworks (ISM, PSPF, Essential Eight).

## Hosting Models

### SaaS (Multi‑Tenant)

In the default SaaS model, PwC (or the service provider) hosts the platform in its own Azure subscription using a multi‑tenant architecture. Customers access the system as a service over the internet. Key characteristics:

Centralised platform services: A common Kubernetes cluster (e.g., Azure Kubernetes Service) hosts core services such as the Agent Orchestrator, connectors, API gateway and data services. Each customer’s data is logically separated using dedicated schemas, resource groups or namespaces to maintain isolation.

Elastic scaling: The cluster scales horizontally based on demand. The Azure Well‑Architected Framework recommends horizontal scaling to add more instances and improve resiliency and capacity[1]. Autoscaling policies ensure that agents and connectors scale independently according to workload.

Managed database and storage: Data is stored in Azure SQL Database or Cosmos DB for structured data, Data Lake Storage for files and analytics, and Azure Search for unstructured search. Encryption at rest and in transit aligns with the security plan.

Network security: Each tenant accesses the system via an API gateway (Azure API Management) with rate limiting and WAF protection. Identity is federated via Open ID Connect using Azure AD or customers’ identity providers. Role‑based access controls apply across agents.

Tenant onboarding: New tenants are provisioned through infrastructure‑as‑code (IaC) templates that create tenant-specific namespaces, database schemas and roles. Tenant metadata is maintained by the Tenant Management service.

### Private Cloud / Single‑Tenant

For clients requiring isolation or adherence to stricter regulatory requirements, the platform can be deployed into the client’s own cloud subscription (Azure, AWS, GCP). The architecture mirrors the SaaS model but provides full tenant isolation:

Dedicated environment: A separate Kubernetes cluster, data storage accounts and networking stack are provisioned for each client. This avoids multi‑tenancy and allows clients to manage their own identity, network controls and security appliances.

Customisable connectors: Clients may enable or disable connectors based on systems in use (e.g., use SAP/Ariba instead of Coupa, or integrate with on‑prem Jira). Connector configuration is managed through IaC variables.

Network connectivity: Private link endpoints, VPN or ExpressRoute connections allow secure integration with on‑prem systems. Ingress is restricted to client networks.

Customer‑controlled compliance: Clients can apply their own compliance controls (e.g., IRAP, FedRAMP) and integrate the platform with their logging and security information and event management (SIEM) systems.

Sovereign cloud: Deployments can target specific regions (e.g., Azure Australia Central) to satisfy data residency requirements. Data replication and backups remain within the region.

### On‑Premises / Air‑Gapped

For highly regulated industries or government agencies requiring air‑gapped environments, the platform can be deployed on‑premises. The same microservices and orchestration framework run on a customer‑provided Kubernetes cluster (e.g., OpenShift, Rancher or AKS on Azure Stack Hub). Considerations:

Infrastructure: The customer must provide and maintain compute, storage and networking. The cluster hosts containerised agents, orchestration services and data stores. Stateful services may use on‑prem database clusters (e.g., SQL Server Always On) or open‑source alternatives.

Offline updates: Container images and updates are delivered via secure media or through a controlled DMZ environment. CI/CD pipelines generate artifacts that can be imported into the air‑gapped environment.

Integration with legacy systems: On‑prem connectors integrate directly with internal systems like SAP, Jira, or local file shares. The Data Synchronisation agent ensures eventual consistency between isolated networks when connectivity is available.

Compliance: The solution must meet strict security controls for on‑prem operations, including offline auditing, patch management and hardware hardening.

## Microservices Architecture

The platform follows a microservices architecture, with each agent, connector and platform capability packaged as a separate container. Advantages include independent scalability, fault isolation and ease of deployment. The Azure Well‑Architected Framework recommends decoupling components and avoiding singletons to support scalability[2]. Microservices communicate via asynchronous message queues (Azure Service Bus/Event Hub) or REST/gRPC APIs.

### Core Components

Agent services: Each of the ~25 agents (Intent Router, Response Orchestration, Approval Workflow, Demand & Intake, Business Case, Portfolio Strategy, etc.) is a stateless microservice exposing APIs and message handlers. Stateless design supports horizontal scaling and resilience.

Connector services: Adapter microservices interface with external systems (Planview, Jira, SAP/Ariba, Workday, Coupa, Slack, Teams, CRM/ERP). They handle authentication, data mapping, throttling and caching. Connectors publish events to the message bus when external data changes.

Orchestration & workflow: The Orchestrator coordinates agent calls, maintains dependency graphs, and aggregates responses. It uses durable workflows (e.g., Azure Durable Functions or Dapr workflows) and an event-driven pattern for long‑running processes.

API Gateway & authentication: Azure API Management (or Istio/Envoy in an on‑prem cluster) provides a unified entry point, request routing, rate limiting and policy enforcement. Identity integration uses OAuth/OIDC with Azure AD, ADFS or third‑party providers. Fine‑grained RBAC is enforced at API endpoints.

Data services: A polyglot persistence layer comprises relational databases (Azure SQL Database/PostgreSQL), NoSQL stores (Cosmos DB, MongoDB), blob storage and Data Lake Storage. A metadata service manages schema definitions and lineage. Data services are accessed via microservices to avoid tight coupling.

Observability: Centralised logging (Azure Monitor, Application Insights), metrics collection and tracing support monitoring and debugging. Logs include correlation IDs across services for traceability.

Infrastructure services: Service discovery (CoreDNS), configuration management (Consul/ConfigMap), secrets management (Azure Key Vault) and certificate management (cert-manager) provide operational support.

### Deployment Topology

Cluster layout: For SaaS and private cloud, the platform runs on one or more Kubernetes clusters. Namespaces or separate clusters segment tenants or environments (dev, test, staging, production). Each agent and connector runs as a Deployment with its own ReplicaSet, enabling independent scaling. Stateful components (databases, message queues) run as managed services or stateful sets with persistent volumes.

Network segmentation: The cluster uses network policies to restrict traffic between microservices. Only necessary ports and protocols are allowed. External traffic flows through the API gateway. Service mesh (e.g., Istio) may provide encryption, observability and traffic shaping between services.

Environment promotion: Lower environments (dev, test, staging) are logically separated with their own resource groups and clusters. Changes progress through these environments via the CI/CD pipeline, allowing validation before production.

## Scaling Strategies

Selecting the correct scaling approach ensures that resources are adjusted efficiently to meet workload demands without overuse or waste[1]. The platform uses a combination of horizontal and vertical scaling:

### Horizontal Scaling

Horizontal scaling adds more instances of a component to distribute the workload across multiple servers. The Azure Well‑Architected Framework notes that horizontal scaling offers improved resiliency, increased capacity and the ability to handle increased traffic for cloud‑native applications[1]. Features include:

Stateless services: Agents are designed stateless where possible. State (sessions, caches) is externalised to Redis or a distributed cache so that any replica can service any request.

Autoscaling: Kubernetes Horizontal Pod Autoscaler (HPA) monitors metrics (CPU, memory, custom metrics like queue length) to scale each agent up or down. Cluster autoscaler adjusts the number of nodes when pods cannot be scheduled.

Queue-based load levelling: To avoid singletons and bottlenecks, processing tasks are partitioned across multiple queues[3]. Fan‑out/fan‑in patterns enable parallel execution.

Microservice independence: Because each agent is a separate microservice, services that experience increased demand (e.g., schedule calculations) can scale independently without affecting others[4].

### Vertical Scaling

Vertical scaling increases the capacity of a single resource (e.g., upgrading to a larger VM). This is appropriate for stateful components that cannot easily be partitioned, such as relational databases or AI models requiring GPU acceleration[5]. Vertical scaling is applied cautiously to avoid overprovisioning.

### Designing for Scalability

To design applications that scale:

Decouple components: Break down the system into independent components that can operate and scale separately[6]. Use well‑defined interfaces and asynchronous messaging[6].

Avoid singletons: Distribute work across multiple queues and tasks instead of centralised resources[3].

Externalise session state: Store session data in an external state store to enable stateless replicas[7].

Monitor and adjust: Continuously monitor resource usage and adjust scaling policies. Use Azure Monitor and Application Insights to collect metrics and set auto‑scale rules.

## CI/CD Pipeline

A well‑designed CI/CD pipeline ensures rapid, reliable delivery of changes across environments. According to Codefresh’s CI/CD best practices, key elements include frequent commits, static code analysis, automated tests, and continuous delivery with validation at each stage[8]. The pipeline is structured into four major phases—source, build, test and deploy—each acting as a checkpoint[9].

### Source Stage

Version control: All source code, configuration and IaC scripts reside in a version control system (e.g., Git). Branching strategies such as trunk‑based development or GitFlow facilitate concurrent development.

Triggers: New commits or pull requests trigger pipeline runs. Pre-commit hooks enforce linting and formatting rules.

### Build Stage

Compilation & packaging: Code is compiled and packaged into container images using Docker. Multi‑stage Dockerfiles produce minimal runtime images. Each agent and connector has its own build definition.

Static analysis & security scanning: Tools run static code analysis and vulnerability scans during the build. If issues are detected, the pipeline fails.

Preliminary tests: Unit tests run in parallel; build artifacts are produced only if tests pass. Codefresh notes that automated tests are executed in the CI process before generating the final build[10].

### Test Stage

Integration & functional tests: After a successful build, integration tests verify agent interactions and connector integrations. Functional tests simulate end‑to‑end scenarios using realistic data.

Performance & security tests: Automated performance tests run against the build in a staging environment; security scans check for vulnerabilities (e.g., dependency scanning, container image scanning).

Artifact promotion: Only passing builds are promoted to staging. Code validation at each stage ensures that quality improves as the code moves through the pipeline[11].

### Deploy Stage

Infrastructure as code: Deployment uses IaC (Terraform, Bicep or Helm charts) to provision resources. The same templates are used across environments to ensure consistency.

Environment-specific configurations: Variables and secrets (stored in Key Vault) are injected during deployment. For private cloud and on‑prem, cluster context and environment-specific connectors are configured via variables.

Release strategies: Deployment strategies include rolling updates, blue‑green deployments and canary releases. Post‑deployment smoke tests and health checks ensure the new version operates correctly. If tests fail, the pipeline automatically rolls back.

Manual approvals: Gate approvals are required before promoting to production, ensuring stakeholder sign‑off and compliance with governance policies.

### Pipeline Best Practices

Single source repository: Maintain code, infrastructure templates and documentation in a single repository[12].

Automate everything: Automate build, test, deployment and environment provisioning[13].

Parallelization: Run tests in parallel where possible to reduce pipeline duration[14].

Artifact management: Store build artifacts (container images, Helm charts, packaged IaC) in a secure registry (Azure Container Registry, Artifactory). Use versioning to enable rollbacks.

Security & compliance: Integrate static application security testing (SAST), dynamic scanning (DAST) and supply chain security scanning into the pipeline. Require secrets to be injected at runtime (never stored in code). Enforce RBAC for pipeline agents and use service principals with least privilege.

Observability & feedback: Use pipeline telemetry (success/failure trends, test coverage, performance metrics) to continuously improve. Fail fast and provide immediate feedback to developers[15].

## Multi‑Environment Support

The platform supports multiple environments and deployment models:

Development & test environments: Provide rapid feedback with minimal data volumes, using lower‑cost compute. Feature branches deploy to isolated namespaces or clusters for developer testing.

Staging environment: Mirrors production configuration and scale as closely as possible. Used for integration tests, performance tests and UAT. Access is limited and sensitive data is masked.

Production environment: Highly available and secure; configured with multiple availability zones and backup policies. Monitoring and alerting are stringent.

Tenant isolation: In SaaS, logical isolation (namespaces, database schemas) ensures tenant data separation. In single‑tenant deployments, physical isolation (dedicated clusters) provides further separation. Networking (VNet, service endpoints) and RBAC enforce isolation.

## Conclusion

The multi‑agent PPM platform’s deployment and infrastructure architecture is designed to be flexible and secure across hosting models. By leveraging microservices, containerisation and Kubernetes, the system scales horizontally to meet demand while allowing vertical scaling for resource‑intensive components. The architecture emphasises decoupling, stateless services and asynchronous communication to avoid bottlenecks and enable independent scaling[1][3]. A comprehensive CI/CD pipeline ensures rapid delivery with rigorous quality gates, automated testing and secure deployment practices[8]. Whether delivered as a SaaS offering, deployed in a private cloud or run on‑premises, this architecture provides a consistent foundation for innovation and compliance.

[1] [2] [3] [4] [5] [6] [7] Architecture strategies for optimizing scaling and partitioning - Microsoft Azure Well-Architected Framework | Microsoft Learn

https://learn.microsoft.com/en-us/azure/well-architected/performance-efficiency/scale-partition

[8] [9] [10] [11] [12] [13] [14] [15] CI/CD Process: Flow, Stages, and Critical Best Practices

https://codefresh.io/learn/ci-cd-pipelines/ci-cd-process-flow-stages-and-critical-best-practices/
