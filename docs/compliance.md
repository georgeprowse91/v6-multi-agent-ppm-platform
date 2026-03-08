# Compliance

> This directory consolidates all compliance documentation for the Multi-Agent PPM Platform, covering applicable regulations, governance model, data classification, retention policy, privacy impact assessment, threat model, audit evidence, certification tracking, and financial-services-specific compliance guidance.

## Contents

- [Overview](#overview)
- [Controls Mapping](#controls-mapping)
- [Data Classification](#data-classification)
- [Data Retention Policy](#data-retention-policy)
- [Consent Mechanism](#consent-mechanism)
- [Privacy DPIA](#privacy-dpia)
- [Threat Model](#threat-model)
- [Audit Evidence Guide](#audit-evidence-guide)
- [Certification Evidence Process](#certification-evidence-process)
- [Financial Services Compliance Management](#financial-services-compliance-management)

---

## Overview

### Applicable regulations

The platform is designed to support compliance with the following core regulatory and assurance frameworks:

- **GDPR**: lawful basis, data minimisation, consent, and retention controls for personal data.
- **SOC 2**: security, availability, confidentiality, and auditability controls.
- **HIPAA**: safeguards for protected health information when healthcare workloads are enabled.

### Platform responsibilities

1. Enforce least-data processing through data minimisation controls.
2. Require valid consent before personal data processing where consent is the legal basis.
3. Capture immutable audit events for sensitive-data access and policy decisions.
4. Apply retention policies and secure disposal procedures by data class and legal requirement.
5. Maintain evidence and operational runbooks for regular control reviews and audits.

### Operating model

- Product and engineering teams implement controls in services and agents.
- Security and compliance teams review control effectiveness and manage exceptions.
- Documentation in this directory is reviewed periodically as regulations and business scope evolve.

---

## Controls Mapping

### Governance model

#### Roles and responsibilities

| Role | Responsibilities |
|------|-----------------|
| **Steering Committee** | Strategic direction, budget approval, and initiative prioritisation. |
| **Data Governance Board** | Data policies, quality standards, classification, privacy compliance, and lineage oversight. |
| **Security & Compliance Officer** | Alignment with ISM, PSPF, ISO 27001, and SOC 2 Type II; risk assessments, penetration tests, and compliance audits. |
| **Risk Management Lead** | Monitors technical, commercial, and adoption risks; coordinates mitigation strategies. |
| **PMO** | Implementation governance, stage-gate approvals, and methodology adherence. |
| **Legal & Privacy Counsel** | Interprets GDPR, Australian Privacy Act, CCPA; maintains data-processing agreements and privacy notices. |
| **Audit & Compliance Team** | Internal and external audits; evidence collection for certifications. |
| **Vendor Management** | Due diligence on third-party providers; ensures contracts include data-processing clauses and right-to-audit terms. |

#### Governance mechanisms

- **Policies**: formal documents covering data usage, retention, acceptable use, remote access, incident response, and change management. Policies reflect classification rules for Public, Internal, Confidential, and Restricted data.
- **Charters & Committees**: each committee operates under a charter detailing scope and decision-making authority; meetings are scheduled regularly with minutes recorded.
- **Escalation paths**: defined procedures for risk issues, compliance breaches, and security incidents, ensuring timely escalation to the appropriate committee.
- **Metrics & reviews**: regular governance reviews measuring compliance metrics (audit findings resolved, data-classification exceptions, mandatory training completion) and approving changes to policies or controls.

### Compliance frameworks

| Framework | Scope |
|-----------|-------|
| **Australian ISM / PSPF** | Mandatory controls for data security, risk management, authentication, encryption, and incident response, including the Essential Eight (application whitelisting, patch management, MFA). |
| **ISO 27001 / ISO 27701** | ISMS covering asset inventories, risk assessments, access control, cryptography, supplier management, business continuity, monitoring, and continual improvement. |
| **SOC 2 Type II** | Annual attestation of security, availability, and confidentiality principles for SaaS deployments. |
| **GDPR & international privacy laws** | Data subject rights, transparency, lawful basis, data minimisation, and cross-border transfer mechanisms (standard contractual clauses). |
| **Australian Privacy Act / NDB Scheme** | Consent, disclosure, and breach notification procedures. |
| **SOX / APRA CPS 234** | Financial reporting controls and prudential information-security obligations. |

### Privacy and data handling

- **Lawful basis**: processing activities documented in a record of processing activities (RoPA), specifying purposes and legal bases.
- **Data subject rights**: processes for access, rectification, deletion, and portability requests.
- **DPIAs**: conducted for new integrations, features, or sensitive-data processing.
- **Consent management**: mechanisms to capture, store, and respect user consent, including granular consent for marketing and analytics.
- **Cross-border transfers**: approved transfer mechanisms, data localisation options, and encryption to protect data in transit.

### Risk assessment and management

- **Regular risk assessments**: at least annually, or upon major changes, to identify technical, operational, and legal risks. Residual risk is documented and mitigation actions are tracked.
- **Threat modelling**: architecture reviewed to identify attack vectors; controls include input validation, output encoding, and secure coding practices.
- **Vendor risk assessments**: third-party providers evaluated for security posture, compliance certifications, and incident history; contracts include breach notification and right-to-audit provisions.
- **Change control**: new functionality undergoes security review, privacy impact assessment, and board approval before production deployment.

### Training and awareness

- **Onboarding and annual training**: mandatory security, privacy, and compliance training for all staff covering data classification, phishing awareness, secure coding, and incident reporting.
- **Role-based training**: specialised content for developers (OWASP Top 10), administrators (hardening and monitoring), and business users (data handling and privacy obligations).
- **Phishing simulations and drills**: periodic campaigns and incident-response exercises.
- **Policy acknowledgements**: employees read and acknowledge policies annually.

### Incident response and data loss prevention

- **Incident response plan**: triage, containment, eradication, and recovery procedures; defined roles (incident commander, communications lead), severity levels, and escalation paths.
- **Forensics and evidence preservation**: immediate collection of logs, system images, and artefacts with chain-of-custody controls.
- **Regulatory notifications**: timely notification to affected users and regulators per the Notifiable Data Breaches scheme.
- **Post-incident review**: root-cause analysis, lessons learned, and remediation actions.
- **DLP**: content inspection, egress monitoring, and policy-based rules to detect and prevent unauthorised transmission of sensitive information.

### Continuous improvement

Governance and compliance requirements are reviewed at least annually and after major incidents or regulatory updates. Feedback from audits, risk assessments, and process mining drives enhancements to the framework.

---

## Data Classification

### Purpose

Define the platform's data classification levels and how they are enforced across services and storage.

### Classification levels

Classification levels are configured in `ops/config/data-classification/levels.yaml` and map to retention policies and permitted roles.

| Level | Description | Retention policy ID | Allowed roles |
|-------|-------------|---------------------|---------------|
| `public` | Publicly shareable information | `public-30d` | tenant_owner, portfolio_admin, project_manager, analyst, auditor, integration_service |
| `internal` | Internal business data with limited exposure | `internal-1y` | tenant_owner, portfolio_admin, project_manager, analyst, auditor |
| `confidential` | Sensitive business data restricted to leadership | `confidential-5y` | tenant_owner, portfolio_admin, project_manager, auditor |
| `restricted` | Highly sensitive data | `restricted-7y` | tenant_owner, portfolio_admin |

### Enforcement points

- **API gateway**: classification in request payloads is evaluated against RBAC rules; unauthorised roles receive masked fields (`services/api-gateway/src/api/middleware/security.py`).
- **Audit log service**: classification drives retention policy selection for audit events (`services/audit-log/src/main.py`).
- **Document service**: classification is evaluated against document policies (`services/document-service/src/document_policy.py`).
- **DLP scanning**: document ingestion and connector payload logging are scanned for sensitive data; findings are blocked or advisory based on `ops/config/security/dlp-policies.yaml`.
- **Assistant prompt safety**: assistant requests are sanitised for prompt-injection markers and blocked or warned before forwarding.
- **Encryption at rest**: document content is encrypted in local storage using Fernet keys provided via secret references.

### DLP enforcement rules

- **Documents**: content and metadata are scanned on ingestion. Blocking findings return HTTP 403 with redacted reasons; advisory findings are returned in the response advisories list.
- **Connector SDK logging**: request/response payloads are redacted before logging to prevent sensitive data leakage.
- **Assistant prompts**: prompt-injection markers are removed from forwarded text, with warnings surfaced to the UI when advisory.

### Encryption at rest scope

- **Document service**: document content is encrypted before persistence and decrypted on read operations.
- **Workspace artefacts**: timeline notes, spreadsheet cell values, and tree notes are scheduled for encryption in a follow-on release if schema changes are required.

### Key management and rotation

- Keys must be provided through secret references (`env:`, `file:`, or Key Vault CSI mounts). Keys are never generated in production.
- To rotate keys: provision a new key, re-encrypt stored documents offline, update secret references, and restart services with the new key.

### Operational guidance

1. Update `ops/config/data-classification/levels.yaml` to reflect customer policy.
2. Align `ops/config/retention/policies.yaml` with classification retention requirements.
3. Validate RBAC role assignments in `ops/config/rbac/roles.yaml` before onboarding users.
4. Ensure DLP policy thresholds in `ops/config/security/dlp-policies.yaml` align with classification expectations.
5. Provide encryption keys via Key Vault / CSI or environment references (`DOCUMENT_ENCRYPTION_KEY`, `ARTIFACT_STORE_ENCRYPTION_KEY`).

### Verification steps

Inspect classification configuration:

```bash
sed -n '1,160p' ops/config/data-classification/levels.yaml
```

Verify retention mapping is present:

```bash
rg -n "retention_policy" ops/config/data-classification/levels.yaml
```

### Implementation status

- **Implemented**: classification config, RBAC enforcement, audit log retention mapping.
- **Implemented**: automated classification tagging in the connector ingestion pipeline.

---

## Data Retention Policy

This section merges content from both the platform retention schedule (`data_retention_policy.md`) and the technical policy configuration reference (`retention-policy.md`).

### Purpose

Define retention and disposal requirements for all key platform data types, and document how those requirements are implemented in configuration and enforced at runtime.

### Retention schedule by data type

| Data type | Typical contents | Retention period | Disposal method |
|-----------|-----------------|-----------------|-----------------|
| Audit events | Policy decisions, access logs, control outcomes | 7 years | Cryptographic erase + immutable store lifecycle expiry |
| Compliance evidence | Control test artefacts, attestations | 5 years | Secure deletion with deletion evidence |
| Risk and issue records | Risk metadata, issue history | 3 years after closure | Secure deletion + index purge |
| Operational telemetry | Traces, metrics, service logs | 90 days (hot), 1 year (archive) | Lifecycle purge |
| Personal data (transactional) | User-submitted PII in workflows | Minimum required; default 1 year unless legal hold applies | Secure deletion and backup expiry |

### Policy set (by classification)

Retention policies are defined in `ops/config/retention/policies.yaml` and referenced by data classification levels in `ops/config/data-classification/levels.yaml`.

| Policy ID | Description | Duration (days) | Storage class |
|-----------|-------------|-----------------|---------------|
| `public-30d` | Public data | 30 | cool |
| `internal-1y` | Internal data | 365 | cool |
| `confidential-5y` | Confidential data | 1,825 | archive |
| `restricted-7y` | Restricted data | 2,555 | archive |

### Disposal controls

- Disposal jobs are automated and policy-driven.
- Deletion operations are logged for auditability.
- Legal hold supersedes standard retention until the hold is formally released.

### Enforcement points

- **Audit log service**: applies retention policies based on classification and writes to immutable storage (`services/audit-log/src/audit_storage.py`).
- **Document service**: evaluates retention rules using document policies (`services/document-service/src/document_policy.py`).
- **Runbook verification**: backup and recovery runbooks include retention validation steps.

### Governance

- Retention periods are reviewed at least quarterly.
- Regulatory and contractual obligations can increase retention windows.

### Operational guidance

1. Update policy durations in `ops/config/retention/policies.yaml` to align with client requirements.
2. Update classification mappings in `ops/config/data-classification/levels.yaml` if policies change.
3. Rotate storage classes in cloud environments to match required durability tiers.

### Verification steps

Inspect retention policies:

```bash
sed -n '1,160p' ops/config/retention/policies.yaml
```

Confirm the audit log service loads retention policies:

```bash
rg -n "RETENTION_CONFIG_PATH" services/audit-log/src/main.py
```

### Implementation status

- **Implemented**: retention policies, audit log enforcement, document policy checks.
- **Implemented**: automated lifecycle management for non-audit data stores via retention schedulers.

---

## Consent Mechanism

### Objective

Ensure personal data is processed only when a valid legal basis exists and, where consent is that basis, it has been explicitly collected and recorded.

### Consent lifecycle

1. **Collection**: explicit consent is requested at data capture points.
2. **Recording**: consent records include subject identifier, purpose, timestamp, and source.
3. **Enforcement**: policy checks verify consent before processing personal data.
4. **Auditability**: each consent-dependent decision is logged in audit events.
5. **Revocation**: revoked consent blocks future processing and triggers downstream restrictions.

### Enforcement in platform services

- Policy controls reject personal-data operations when consent is missing.
- Data minimisation removes unneeded fields and masks sensitive fields.
- Agents handling sensitive workflows call compliance policy checks before action execution.

### Team procedure

- Review this mechanism during onboarding for engineering, product, and operations teams.
- Run periodic table-top scenarios for consent revocation and subject-access workflows.
- Record attendance and updates in the compliance training tracker.

---

## Privacy DPIA

### Platform DPIA — Multi-Agent PPM Platform

#### 1. Project overview

| Field | Details |
|-------|---------|
| **System name** | Multi-Agent PPM Platform |
| **Purpose** | Portfolio, program, project, budget, and risk management with multi-agent orchestration, audit logging, and policy enforcement. |
| **Deployment model** | Azure Kubernetes Service (AKS) with managed Postgres, Redis, and Blob Storage. Infrastructure defined in Terraform (`ops/infra/terraform/main.tf`). |

#### 2. Data processing summary

**Data subjects**
- Internal employees (portfolio managers, project managers, auditors, administrators).
- External partners (vendors) where vendor contacts are stored.

**Categories of personal data**
- **Identifiers**: user IDs, tenant IDs, role assignments, audit actor IDs.
- **Contact data (limited)**: vendor owner or contact names.
- **Operational metadata**: access tokens (validated only, not persisted), request metadata (trace/correlation IDs).

**Special category data**: none processed by design. Classification controls restrict sensitive payloads at ingestion and in audit events.

**Data flows**
1. API Gateway receives user requests and forwards to services.
2. Domain services persist business data (projects, budgets, risks) to Postgres.
3. Audit Log service writes immutable events to WORM storage with retention metadata.
4. Analytics jobs read curated datasets and emit aggregated metrics.

**Data storage locations**
- **Relational data**: Azure Database for PostgreSQL (geo-redundant backups enabled).
- **Audit logs**: Azure Blob Storage with immutability policies (or encrypted local WORM storage for development environments).
- **Configuration**: Azure Key Vault for secrets and Kubernetes ConfigMaps for non-secret settings.

#### 3. Lawful basis and purpose limitation

- Processing is required to deliver contracted portfolio management services (contractual necessity).
- Audit logging supports security and compliance obligations (legitimate interests).
- Data is used only for operational, compliance, and reporting purposes; no advertising or secondary use.

#### 4. Data minimisation and retention

- Only required identifiers, role data, and operational metadata are stored.
- Retention policies are enforced per classification (`ops/config/retention/policies.yaml`) with automated pruning.
- Audit events include `retention_policy` and `retention_until` fields to enforce deletion after expiry.

#### 5. Security measures

- Authentication and tenant isolation enforced by `AuthTenantMiddleware`.
- Audit log events are stored in encrypted, write-once storage with immutability checks.
- Secrets stored in Azure Key Vault; no secrets embedded in code or configs.
- TLS enforced for service ingress and managed databases.

#### 6. Data subject rights support

- Requests for access, correction, or deletion are handled through tenant administrators.
- Audit logs remain immutable, but access to events is restricted via role-based access controls.
- Deletion requests trigger downstream deletions and retention enforcement where legally permitted.

#### 7. Risk assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| Unauthorised tenant data access | High | Low | JWT verification, tenant scoping middleware, RBAC policy checks. |
| Audit log tampering | High | Low | WORM storage, encryption, immutability enforcement tests. |
| Over-retention of data | Medium | Low | Automated retention enforcement and tests. |
| Data loss | High | Low | Geo-redundant backups, recovery runbooks, restore drills. |

#### 8. DPIA outcome

Residual risk is **low** after applying access controls, encryption, retention enforcement, and audit logging. The platform may process additional personal data only after updating this DPIA and completing a privacy review. This DPIA is **complete** for the current release scope and is tied to release readiness sign-off.

#### 9. Review cadence

- **Trigger events**: new integrations, new data categories, or changes to retention/encryption.
- **Scheduled review**: every 6 months or before major releases.
- **Evidence**: update `docs/production-readiness/evidence-pack.md` with review notes.

#### 10. Approvals

| Role | Status | Evidence |
|------|--------|---------|
| Data Protection Officer | Completed | Release readiness checklist |
| Security Lead | Completed | Release readiness checklist |
| Product Owner | Completed | Release readiness checklist |

---

### DPIA Blank Template

Use this template when completing a DPIA for new processing activities, significant changes to existing processing, or when required by regulation or policy.

**Audience**: Privacy Officer, Security Lead, Data Protection Officer, Product Owner, Legal Counsel.

**Inputs required**:
- System architecture diagrams and data flow maps.
- Data inventory and classification details.
- Security and compliance requirements.
- Vendor and sub-processor information.

**Definitions**:
- **Personal data**: information relating to an identified or identifiable person.
- **Special category data**: sensitive data requiring additional safeguards.
- **Data subject**: the individual whose personal data is processed.

#### Assessment metadata

| Field | Value |
|-------|-------|
| Assessment ID | |
| Project / Product name | |
| Assessment owner | |
| Date initiated | |
| Date completed | |
| Review cadence | |

#### Section 2 — Processing overview

**2.1 Description of processing**: describe the processing activities, including the business purpose and outcomes.

**2.2 Legal basis**

| Processing Activity | Legal Basis | Justification |
|---------------------|-------------|---------------|
| | | |

**2.3 Data categories**

| Data Category | Examples | Special Category | Retention Period |
|---------------|----------|-----------------|-----------------|
| | | | |

**2.4 Data subjects**

| Data Subject Group | Description | Volume |
|--------------------|-------------|--------|
| | | |

**2.5 Data sources and destinations**

| Source System | Destination System | Transfer Type | Purpose |
|---------------|--------------------|---------------|---------|
| | | | |

#### Section 3 — Data flow and storage

**3.1 Data flow summary**: include a high-level description of where data enters, is processed, stored, and shared.

**3.2 Storage locations**

| Storage Location | Region | Encryption | Access Controls |
|-----------------|--------|-----------|----------------|
| | | | |

#### Section 4 — Risk assessment

**4.1 Identified risks**

| Risk ID | Risk Description | Likelihood | Impact | Existing Controls |
|---------|-----------------|-----------|--------|------------------|
| | | | | |

**4.2 Mitigation plan**

| Risk ID | Mitigation Action | Owner | Due Date | Status |
|---------|------------------|-------|---------|--------|
| | | | | |

#### Section 5 — Security and compliance controls

| Control Area | Control Description | Evidence |
|-------------|---------------------|---------|
| Access Management | | |
| Encryption | | |
| Logging & Monitoring | | |
| Incident Response | | |
| Data Minimization | | |
| Vendor Management | | |

#### Section 6 — Data subject rights

Describe how data subject rights are supported, including access, correction, deletion, and objection workflows.

#### Section 7 — Data retention and disposal

| Data Category | Retention Period | Disposal Method | Owner |
|---------------|-----------------|----------------|-------|
| | | | |

#### Section 8 — Third-party and international transfers

| Vendor / Sub-processor | Data Shared | Transfer Mechanism | Safeguards |
|------------------------|------------|-------------------|-----------|
| | | | |

#### Section 9 — Residual risk evaluation

Summarise residual risks after mitigation and whether additional approvals are required.

#### Section 10 — Approvals and sign-off

| Approver | Role | Decision | Date |
|----------|------|---------|------|
| | | | |

#### Completion checklist

- [ ] Processing activities documented with legal basis.
- [ ] Data categories and data subject groups identified.
- [ ] Risks assessed with mitigation actions.
- [ ] Security and compliance controls documented.
- [ ] Approvals recorded.

#### Acceptance criteria

- DPIA covers data flows, risks, and controls with actionable mitigations.
- Residual risks are accepted or escalated per governance.
- Sign-offs align with compliance requirements.

---

## Threat Model

### Purpose

Document the security threat model for the Multi-Agent PPM Platform, focusing on primary assets, trust boundaries, and mitigations that protect tenant data, workflows, and audit trails.

### Scope

- API Gateway, Workflow Service, orchestration layer, and core services.
- Data stores: Postgres, Redis, and immutable audit storage.
- External integrations: connectors to PPM, ERP, and collaboration systems.

### Assets

- Tenant data (projects, budgets, risks, workflows).
- Audit logs and lineage data.
- Identity data and access tokens.
- Configuration secrets and signing keys.

### Trust boundaries

1. **User to ingress** — public API boundary.
2. **Service-to-service communication** — within the cluster.
3. **Service to data stores** — Postgres, Redis, blob/WORM storage.
4. **Connectors to external systems** — Jira, SAP, Workday, Teams, and others.

### Threats and mitigations (STRIDE)

| Threat | Example scenario | Mitigations | Detection / Response |
|--------|-----------------|------------|---------------------|
| Spoofing | Forged JWT or tenant headers used to impersonate a user. | JWT validation, tenant middleware, SCIM-managed identities, MFA enforcement via IdP. | Auth error alerts, audit log correlation IDs, anomalous login alerts. |
| Tampering | Modification of audit events or workflow data. | WORM storage for audit logs, database integrity constraints, signed artefacts for releases. | Audit log immutability checks, DB integrity alerts. |
| Repudiation | Users deny actions taken in the system. | Immutable audit log entries, trace/correlation IDs, least-privilege roles. | Audit review reports, access log retention. |
| Information disclosure | Sensitive data exposed via misconfigured endpoints. | RBAC/ABAC policies, data classification, encryption in transit and at rest. | DLP alerts, config drift monitoring. |
| Denial of service | Flooding API or sync endpoints. | Rate limiting, autoscaling, queue backpressure, circuit breakers. | SLO alerts, throttling dashboards. |
| Elevation of privilege | Role escalation through misconfigured policies. | Policy engine validation, separation of duties, config reviews. | Policy evaluation logs, periodic access reviews. |

### High-risk areas and controls

1. **Connector integrations**
   - Risk: unauthorised data ingress or egress.
   - Controls: scoped credentials, per-connector allowlists, sync audit events.

2. **Audit log pipeline**
   - Risk: loss of compliance evidence.
   - Controls: WORM storage, retention enforcement, automated integrity checks.

3. **Policy enforcement**
   - Risk: inconsistent access decisions across services.
   - Controls: centralised policy engine, shared policy contracts, regression tests.

### Assumptions

- All services communicate over mTLS or private network paths.
- Secrets are stored in a managed vault (Azure Key Vault).
- Production environments enforce least-privilege IAM policies.

### Residual risks

- Connector API changes can introduce unexpected data exposures.
- Misconfiguration risk remains if infrastructure-as-code reviews are bypassed.

### Review cadence

Reassess before every major release or when a new external integration is introduced. Record results in `docs/production-readiness/evidence-pack.md`.

---

## Audit Evidence Guide

### Purpose

Enumerate auditable evidence sources and explain how to collect them for compliance reviews.

### Evidence categories

| Evidence type | Source | Validation steps |
|--------------|--------|-----------------|
| Audit log events | `services/audit-log` storage | Query `/v1/audit/events/{id}` and verify retention metadata. |
| Retention policies | `ops/config/retention/policies.yaml` | Confirm retention durations and storage class. |
| Data classification | `ops/config/data-classification/levels.yaml` | Validate classification-to-retention mappings. |
| RBAC configuration | `ops/config/rbac/*.yaml` | Review roles, permissions, and field masking rules. |
| Infrastructure as code | `ops/infra/terraform/` | Validate Terraform plan/apply evidence. |
| Helm deployments | `apps/*/helm`, `services/*/helm` | Archive Helm release manifests. |
| CI/CD validation | `.github/workflows/*.yml` | Store CI logs for docs checks, linting, and tests. |

### Evidence collection workflow

1. **Audit log samples**: pull a representative sample of audit events from the audit log service.
2. **Configuration snapshot**: export the latest `ops/config/` directory for the tenant.
3. **Deployment evidence**: save Terraform plans and Helm release manifests.
4. **CI logs**: archive CI runs proving schema, manifest, and doc validation.

### Verification steps

Confirm audit log service schema validation:

```bash
rg -n "audit-event.schema.json" services/audit-log/src/main.py
```

Validate the retention policy file exists:

```bash
ls ops/config/retention/policies.yaml
```

### Implementation status

- **Implemented**: audit log service, retention policies, RBAC configuration.
- **Implemented**: automated evidence pack export via `/v1/audit/evidence/export` and web console trigger.

---

## Certification Evidence Process

**Owner**: Compliance Lead / Platform Operations
**Last reviewed**: 2026-02-20

The web console includes a certification evidence workflow for connector coverage. Each connector can store a compliance status, certification dates, and attached audit documents (SOC reports, ISO certificates, or regulator attestations).

### What gets tracked

- **Compliance status**: certified, pending, expired, or not certified.
- **Certification dates**: issuance and expiration dates.
- **Audit reference**: external report IDs or links from auditors.
- **Evidence documents**: uploaded files stored alongside connector metadata.

### How to update evidence in the web console

1. Navigate to **Marketplace → Connectors**.
2. Select **Manage Evidence** on a connector card.
3. Update the compliance status, dates, and audit reference.
4. Upload evidence documents (PDFs, certificates, audit reports).
5. Save to persist the record.

### Storage and API integration

- Certification metadata is stored persistently in `data/connectors/certifications.json` (configurable via `CERTIFICATION_STORE_PATH`).
- Evidence documents are stored under `data/connectors/certification_documents/` (configurable via `CERTIFICATION_DOCUMENT_ROOT`).
- The API gateway exposes `/v1/certifications` for listing, creating, and updating records, and `/v1/certifications/{connector_id}/documents` for evidence uploads.

### Operational checklist

- Schedule periodic reviews for upcoming certification expirations.
- Attach external audit artefacts whenever a certification status changes.
- Use the audit reference field to cross-link external compliance systems.

---

## Financial Services Compliance Management

This section is based on the Australian Financial Services Compliance Management Template (v1.0) and provides structured guidance for managing compliance in financial services projects delivered on this platform.

### Overview

#### Purpose and scope

This framework provides a systematic approach to identifying, monitoring, and reporting compliance obligations throughout the project lifecycle, ensuring alignment with Australian regulatory requirements and organisational compliance policies.

**In scope**: new product/service development, system implementations and technology upgrades, business process changes, mergers and acquisitions, outsourcing arrangements, and market expansions.

**Out of scope**: enterprise-wide compliance management system (addressed separately); business-as-usual compliance activities unrelated to projects; detailed procedures for specific regulations (see appendices).

**Framework objectives**:
- Ensure consistent identification and management of compliance requirements.
- Establish clear accountability for compliance-related activities.
- Provide a structured methodology for compliance risk assessment.
- Facilitate timely and accurate regulatory reporting.
- Support audit readiness and evidence collection.
- Minimise compliance incidents and regulatory exposure.
- Foster a culture of compliance within project teams.

#### Roles and responsibilities

| Role | Responsibilities |
|------|-----------------|
| **Project Sponsor** | Ultimate accountability for project compliance; provides resources; reviews critical compliance decisions. |
| **Project Manager** | Integrates compliance activities into the project plan; ensures milestones are met; escalates issues. |
| **Compliance Officer / Lead** | Identifies requirements; performs risk assessments; reviews deliverables; develops testing approach. |
| **Legal Counsel** | Interprets regulatory requirements; reviews contracts; advises on regulatory implications. |
| **Business / Product Owner** | Ensures business requirements include compliance needs; approves compliance-related design decisions. |
| **Technology Team** | Implements technical controls; documents system compliance features; supports compliance testing. |
| **Risk Management** | Assesses compliance risk impact; ensures alignment with enterprise risk framework. |
| **Quality Assurance** | Includes compliance requirements in test plans; executes and documents compliance test results. |

#### RACI matrix for key compliance activities

| Activity | Project Sponsor | Project Manager | Compliance Officer | Legal | Business Owner | Technology | Risk Mgmt | QA |
|----------|-----------------|-----------------|--------------------|-------|----------------|------------|-----------|-----|
| Requirements identification | I | A | R | C | C | I | C | I |
| Risk assessment | A | R | R | C | C | C | R | I |
| Controls design | I | A | R | C | C | R | C | I |
| Documentation | I | A | R | C | C | C | I | C |
| Compliance testing | I | A | R | I | C | C | I | R |
| Regulatory reporting | I | I | R | C | I | C | I | I |
| Training | I | A | R | C | C | C | I | I |
| Incident management | I | A | R | C | C | C | C | I |

*R = Responsible, A = Accountable, C = Consulted, I = Informed*

#### Australian regulatory landscape

Australian financial services projects must navigate a complex regulatory environment.

| Regulatory area | Key regulations / standards | Project implications |
|-----------------|----------------------------|---------------------|
| **Prudential Standards** | APRA CPS 230, CPS 234, CPS 231 | Operational resilience controls; security governance and testing; third-party oversight. |
| **Financial Services Licensing** | Corporations Act 2001; ASIC RG 104, RG 146 | Advice/product governance; disclosure obligations; training and competency controls. |
| **Anti-Money Laundering** | AML/CTF Act 2006; AUSTRAC Rules | Customer due diligence; transaction monitoring; suspicious matter reporting. |
| **Payments & Consumer Protection** | ePayments Code; ASIC RG 271 | Dispute handling timelines; customer communications and transparency. |
| **Data Protection & Privacy** | Privacy Act 1988 (APPs); NDB Scheme | Consent and purpose limitation controls; breach notification procedures. |
| **Open Banking & Data Sharing** | Consumer Data Right (CDR) | Consent management; accreditation and security obligations. |
| **Critical Infrastructure** | SOCI Act | Risk management programs; enhanced cyber obligations. |
| **Industry Standards** | PCI DSS; ISO 27001/27701 | Secure payment processing controls; ISMS expectations. |

**Regulatory considerations**:
- Regulatory change monitoring is required throughout the project lifecycle.
- Service providers and cloud vendors often trigger APRA CPS 231/CPS 230 obligations.
- Breach notification timelines must align with the NDB scheme and APRA/ASIC expectations.
- Data residency and cross-border transfer controls must align with APP 8 and contractual obligations.

---

### Compliance requirements matrix

#### Requirements identification process

1. **Initial regulatory assessment**: identify project scope; determine regulators (APRA/ASIC/AUSTRAC); identify customer segments, products/services, and technology components impacted.
2. **Regulatory inventory review**: consult the enterprise regulatory inventory and change management system; identify applicable regulations and specific requirements.
3. **Requirements documentation**: catalogue all applicable requirements; link to project components; identify dependencies; prioritise by risk and impact.

#### Requirements mapping template

| Requirement ID | Requirement Description | Regulatory Source | Jurisdiction | Project Component | Owner | Priority | Implementation Approach | Verification Method |
|----------------|-------------------------|-------------------|--------------|-------------------|-------|----------|--------------------------|---------------------|
| REQ-AML-001 | CDD must capture minimum customer identification | AML/CTF Act 2006 + AUSTRAC Rules | AU | Customer onboarding | KYC Team Lead | High | Enhanced data collection, ID verification | Process walkthrough, sample testing |
| REQ-PRIV-001 | Personal information collected for a clear stated purpose | Privacy Act 1988 (APP 3/5/6) | AU | Account opening, analytics | Privacy Officer | High | Consent notices, purpose statements | UI review, data flow assessment |
| REQ-APRA-001 | Information security controls aligned with CPS 234 | APRA CPS 234 | AU | Platform security | Security Lead | High | Security control implementation and monitoring | Control testing, audit evidence |

#### Example — Digital payments project

| Requirement ID | Requirement Description | Regulatory Source | Jurisdiction | Project Component | Owner | Priority | Implementation Approach | Verification Method |
|----------------|-------------------------|-------------------|--------------|-------------------|-------|----------|--------------------------|---------------------|
| REQ-PAY-001 | Dispute resolution timeframes aligned with ePayments Code | ePayments Code | AU | Dispute workflow | Operations Manager | High | SLA enforcement, workflow timers | Process testing, sample case review |
| REQ-PAY-002 | Significant cyber incidents reported per CPS 234 timelines | APRA CPS 234 | AU | Incident response | Security Manager | High | Incident notification playbooks | Tabletop exercises, evidence review |
| REQ-PAY-003 | Payment card data storage meets PCI DSS | PCI DSS | AU | Payments platform | Security Architect | Medium | Tokenisation, segmentation, encryption | Pen testing, PCI evidence review |

#### Control frameworks

**Control design principles**:

1. **Risk-based approach**: focus control resources on highest-risk areas; design control intensity proportional to risk level.
2. **Multiple control types**:
   - **Preventive**: stop non-compliance before it occurs.
   - **Detective**: identify non-compliance after it occurs.
   - **Corrective**: address non-compliance once detected.
   - **Directive**: provide guidance to ensure compliance.
3. **Control integration**: embed controls within business processes; automate where possible; minimise operational burden.
4. **Control documentation**: define control objective and regulatory linkage; document design, operation, frequency, responsibility, and evidence requirements.

#### Control matrix template

| Control ID | Control Description | Control Type | Control Owner | Regulatory Requirement(s) | Control Frequency | Evidence Required | Testing Approach | Systems / Tools |
|------------|---------------------|-------------|---------------|---------------------------|-------------------|-------------------|-----------------|-----------------|
| CTL-001 | Customer identity verification using two independent sources | Preventive | KYC Team Lead | REQ-AML-001 | At onboarding | Verification logs, timestamps | Sample testing, walkthrough | ID verification system |
| CTL-002 | Security control assurance aligned to CPS 234 | Detective | Security Operations | REQ-APRA-001 | Quarterly | Security assessment reports | Control testing, audit review | Security monitoring platform |
| CTL-003 | Privacy consent capture for data sharing | Preventive | Privacy Officer | REQ-PRIV-001 | At data capture | Consent logs, UI screenshots | UX testing, data flow review | Consent management system |

#### Reporting obligations

| Report ID | Report Name | Recipient | Frequency | Deadline | Approval Requirements | Submission Method | Retention | Owner |
|-----------|-------------|-----------|-----------|----------|-----------------------|-------------------|-----------|-------|
| RPT-REG-001 | Suspicious Matter Report (SMR) | AUSTRAC | Ad-hoc | As required | MLRO | AUSTRAC Online | 7 years | AML Team |
| RPT-REG-002 | CPS 234 Incident Notification | APRA | Ad-hoc | Within required timelines | CISO | Secure portal/email | 7 years | Security Team |
| RPT-INT-001 | Compliance Status Report | Compliance Committee | Monthly | 5th business day | Compliance Officer | Email, portal | 7 years | Compliance Lead |

---

### Compliance monitoring program

#### Testing and surveillance

**Testing documentation template**

| Test ID | Test Name | Compliance Requirement(s) | Test Type | Description | Sample | Expected Outcome | Tester | Test Date |
|---------|-----------|---------------------------|-----------|-------------|--------|-----------------|--------|-----------|
| TST-001 | Customer Due Diligence Verification | REQ-AML-001 | Implementation | Verify CDD process collects and validates required information | 25 random accounts | All required fields collected and validated | [Name] | [Date] |
| TST-002 | CPS 234 Control Assurance | REQ-APRA-001 | Operational | Verify security controls are monitored and tested | Quarterly sample | Controls operating as designed | [Name] | [Date] |

**Surveillance activities**

| Activity Type | Description | Frequency | Responsibility | Documentation |
|--------------|-------------|-----------|----------------|---------------|
| Control Monitoring | Tracking control execution and effectiveness | Daily / Weekly / Monthly | Control Owners | Monitoring dashboards, exception logs |
| Regulatory Change Monitoring | Tracking relevant regulatory developments | Ongoing | Compliance Officer | Regulatory change log |
| Issue Tracking | Following compliance issues to resolution | Ongoing | Project Manager | Issue register |

#### Review schedules

| Review Type | Purpose | Frequency | Participants | Outputs |
|-------------|---------|-----------|--------------|---------|
| Requirements Review | Ensure all compliance requirements are identified | Project initiation, scope changes | Project team, Compliance, Legal | Requirements register, gaps/actions |
| Design Review | Verify compliance requirements are in solution design | Design phase completion | Design team, Compliance, Business | Design compliance assessment |
| Pre-Implementation Review | Final verification before go-live | Prior to implementation | Project team, Compliance, Risk | Implementation readiness assessment |
| Post-Implementation Review | Verify compliance in production | 30–60 days after go-live | Project team, Compliance | Compliance report |
| Periodic Compliance Review | Ongoing verification of compliance status | Quarterly / Bi-annually | Compliance, Business | Compliance assessment |

#### Documentation requirements

| Category | Purpose | Key Documents | Retention Period | Access Control |
|---------|---------|---------------|-----------------|----------------|
| Requirements Documentation | Demonstrate understanding of compliance obligations | Requirements register, regulatory analysis | Project duration + 7 years | Compliance team, project team |
| Testing Documentation | Demonstrate verification of compliance | Test plans, test results, issues | Project duration + 5 years | QA, compliance |
| Control Evidence | Demonstrate control effectiveness | Control execution logs, approvals | 7 years | Control owners, compliance |
| Regulatory Reporting | Demonstrate regulator communication | Report copies, receipts | 7–10 years | Reporting, compliance |

---

### Reporting framework

#### Internal reporting structure

| Audience | Focus Areas | Format | Frequency | Content |
|----------|------------|--------|-----------|---------|
| Project Team | Compliance task status, issues | Dashboard, status report | Weekly | RAG status, action items |
| Steering Committee | Overall compliance status, key risks | Executive summary | Monthly | Status highlights, decisions needed |
| Compliance Function | Control effectiveness, testing results | Detailed report | Monthly | Requirements status, test results |
| Executive Leadership | Material compliance risks | Executive brief | Quarterly | Risk overview, resource needs |

#### External and regulatory reporting process

1. **Requirement identification**: identify applicable reporting obligations.
2. **Report development**: define data sources, validation, and quality controls.
3. **Review and approval**: define review responsibilities and sign-offs.
4. **Submission process**: define submission procedures and contingency plans.
5. **Post-submission activities**: capture evidence and address follow-up queries.

#### Incident reporting procedures

| Incident Level | Description | Examples | Initial Reporting Timeframe | Key Stakeholders |
|----------------|-------------|----------|----------------------------|-----------------|
| **Critical** | Significant regulatory breach with material impact | Data breach with material impact; major AML violation | Immediate (within 1–4 hours) | Executives, Board, Regulators, Legal, Compliance |
| **Major** | Serious compliance failure | Systematic control failure | Same day | Executives, Legal, Compliance |
| **Moderate** | Limited impact compliance issue | Control deficiency | 24–48 hours | Compliance, Risk, PM |
| **Minor** | Minimal impact procedural issue | Documentation gap | Within 1 week | Project Manager, Compliance Team |

---

### Training and communication

#### Training requirements

| Training Element | Target Audience | Delivery Method | Duration | Frequency | Assessment Method |
|-----------------|----------------|-----------------|----------|-----------|------------------|
| Regulatory Overview | All project team members | E-learning | 1 hour | Project start, major updates | Quiz |
| APRA CPS 234/CPS 230 | Security, Operations | Workshop | 2 hours | Annually | Participation exercise |
| AML/CTF | AML team, Operations | E-learning | 1 hour | Annually | Quiz |

#### Communication protocols

| Information Type | Sender | Recipient | Timing | Method | Response Expected |
|-----------------|--------|-----------|--------|--------|-----------------|
| Compliance Requirements Updates | Compliance Lead | Project Team | Initial + when changed | Email, repository | Acknowledgment |
| Compliance Issues | Any team member | Compliance Lead | Upon discovery | Issue tracking system | Acknowledgment, guidance |
| Regulatory Changes | Compliance Team | Project Team | When identified | Email, change notice | Implementation plan |

---

### Appendices

#### Appendix A — Key Australian regulatory requirements reference

| Regulation | Key project implications | Common requirements |
|------------|--------------------------|---------------------|
| **APRA CPS 230** | Operational risk management and resilience | Service provider oversight, incident management, BCP testing |
| **APRA CPS 234** | Information security governance and assurance | Security testing, incident notification, control monitoring |
| **AML/CTF Act** | AML program design and reporting | Customer due diligence, SMR reporting, transaction monitoring |
| **Privacy Act (APPs)** | Data collection, use, disclosure | Consent, purpose limitation, cross-border controls |
| **CDR** | Data sharing and consent | Consent management, accreditation security requirements |
| **SOCI Act** | Critical infrastructure risk management | Reporting, enhanced cyber obligations |

#### Appendix B — Compliance documentation templates

**Compliance Requirements Register fields**

| Field | Description |
|-------|-------------|
| Requirement ID | Unique identifier (e.g., REQ-AML-001) |
| Requirement Name | Short descriptive name |
| Requirement Description | Detailed description |
| Regulatory Source | Specific regulation, article, section |
| Applicability | Project components where requirement applies |
| Implementation Approach | How the requirement will be implemented |
| Controls | Controls that satisfy this requirement |
| Verification Method | How compliance will be verified |
| Risk Level | Impact of non-compliance (High / Medium / Low) |
| Owner | Person responsible for implementation |
| Status | Current implementation status |
| Evidence Location | Where compliance evidence is stored |
| Notes | Additional information or context |

**Compliance Test Plan fields**

| Field | Description |
|-------|-------------|
| Test ID | Unique identifier (e.g., TST-AML-001) |
| Test Name | Descriptive name |
| Requirements Covered | Requirements being tested |
| Test Objective | What the test aims to verify |
| Test Description | Detailed test procedure |
| Prerequisites | Conditions required for testing |
| Test Data | Data needed for execution |
| Expected Results | What constitutes success |
| Pass/Fail Criteria | Specific evaluation criteria |
| Test Owner | Person responsible for execution |
| Planned Date | When the test will be conducted |
| Actual Date | When the test was conducted |
| Result | Pass / Fail / Partial |
| Issues Found | Description of any issues |
| Evidence Location | Where test evidence is stored |
| Notes | Additional information |

**Compliance Risk Assessment fields**

| Field | Description |
|-------|-------------|
| Risk ID | Unique identifier (e.g., RSK-AML-001) |
| Risk Description | Detailed description |
| Risk Category | Type of compliance risk |
| Regulatory Impact | Specific regulatory consequences |
| Probability | Likelihood (1–5) |
| Impact | Severity (1–5) |
| Inherent Risk Score | Probability × Impact before controls |
| Key Controls | Controls that mitigate this risk |
| Control Effectiveness | Effectiveness rating (1–5) |
| Residual Risk Score | Risk level after controls |
| Risk Owner | Person responsible |
| Mitigation Actions | Additional actions to reduce risk |
| Monitoring Approach | How the risk will be monitored |
| Review Frequency | How often the risk is reassessed |
| Notes | Additional information |

**Regulatory Interaction Log fields**

| Field | Description |
|-------|-------------|
| Interaction ID | Unique identifier (e.g., REG-001) |
| Regulator | Name of regulatory body |
| Interaction Date | When the interaction occurred |
| Interaction Type | Meeting, inquiry, examination, etc. |
| Participants | Persons involved |
| Topics Discussed | Subject matter |
| Key Points | Important information exchanged |
| Regulator Feedback | Input received from regulator |
| Action Items | Required follow-up actions |
| Due Date | When actions must be completed |
| Status | Current status of action items |
| Documentation | Location of interaction records |
| Follow-up | Subsequent interactions or updates |
| Notes | Additional information |

#### Appendix C — Glossary

| Term | Definition |
|------|------------|
| **AFSL** | Australian Financial Services Licence |
| **AML/CTF** | Anti-Money Laundering and Counter-Terrorism Financing |
| **APRA** | Australian Prudential Regulation Authority |
| **ASIC** | Australian Securities and Investments Commission |
| **AUSTRAC** | Australian Transaction Reports and Analysis Centre |
| **CDR** | Consumer Data Right |
| **CPS 230/234** | APRA Prudential Standards for operational risk and information security |
| **NDB** | Notifiable Data Breaches Scheme |
| **SOCI** | Security of Critical Infrastructure Act |
| **SMR** | Suspicious Matter Report |
