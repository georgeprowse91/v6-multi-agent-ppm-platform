# System Context

## Purpose

Describe who uses the Multi-Agent PPM Platform, the external systems it integrates with, and the high-level system boundary. This document anchors the logical and physical architecture in the real enterprise ecosystem.

## Architecture-level context

The platform sits between portfolio stakeholders (PMO, delivery leads, finance, resource managers) and enterprise systems of record (PPM, ERP, HR, CRM, collaboration). It provides a unified AI-assisted workflow while preserving those systems as sources of truth. The system context diagram in `docs/architecture/diagrams/c4-context.puml` captures the boundary and integrations.

## System boundary and actors

**Primary actors**
- Portfolio leaders and PMO staff using the web experience.
- Project and program managers collaborating with agents.
- Finance, resource, and compliance stakeholders reviewing gates and approvals.

**External systems**
- PPM/work management: Jira, Azure DevOps, Planview, Clarity PPM, Monday.com, Asana, Smartsheet, Microsoft Project Server.
- ERP/Finance: SAP, Workday, Oracle ERP Cloud, NetSuite.
- HR/Workforce: ADP, SAP SuccessFactors.
- GRC/Risk: RSA Archer, LogicGate, ServiceNow GRC.
- CRM: Salesforce.
- Identity: Azure AD / Okta.
- Collaboration: Slack, Microsoft Teams, Microsoft 365, SharePoint, Confluence, Google Drive, Google Calendar, Outlook, Zoom.
- Communications: Twilio, Azure Communication Services, Azure Notification Hubs.
- IoT: IoT device telemetry integrations.

**System boundary**
The platform orchestrates tasks and maintains a canonical data model. It does **not** replace upstream systems of record; connectors synchronize data bi-directionally based on policy.

## Diagram

```text
PlantUML: docs/architecture/diagrams/c4-context.puml
```

## Usage example

View the system context diagram source:

```bash
sed -n '1,160p' docs/architecture/diagrams/c4-context.puml
```

## How to verify

Confirm the diagram file exists:

```bash
ls docs/architecture/diagrams/c4-context.puml
```

Expected output: the PlantUML file path.

## Implementation status

- **Implemented**: documentation and diagram source.
- **Implemented**: connector registry includes the full set of documented external systems.

## Related docs

- [Logical Architecture](logical-architecture.md)
- [Connector Overview](../connectors/overview.md)
- [Agent Orchestration](agent-orchestration.md)
