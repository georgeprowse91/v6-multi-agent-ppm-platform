# Connector Inventory: Operations + MCP Coverage

## Sources of truth
- Connector packages under `integrations/connectors/`, including each `*connector.py` and any `mappers.py`.
- `integrations/connectors/sdk/src/connector_registry.py` for SDK-level connector definitions (including MCP metadata).
- `integrations/connectors/registry/connectors.json` for current registry status and sync directions.
- MCP connector manifests in `integrations/connectors/*_mcp/manifest.yaml`.

## Inventory by system

### ADP
- **Connector IDs:** `adp`
- **Sync directions:** inbound
- **REST operations:**
  - **Read:** workers, payroll
  - **Write:** none

### Archer (RSA Archer)
- **Connector IDs:** `archer`
- **Sync directions:** inbound
- **REST operations:**
  - **Read:** risks
  - **Write:** none

### Asana
- **Connector IDs:** `asana`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** projects, tasks
  - **Write:** tasks

### Azure DevOps
- **Connector IDs:** `azure_devops`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** projects, work items
  - **Write:** work items

### Azure Communication Services
- **Connector IDs:** `azure_communication_services`
- **Sync directions:** outbound
- **REST operations:**
  - **Read:** sms, email
  - **Write:** sms (send), email (send)

### Clarity PPM
- **Connector IDs:** `clarity`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** projects
  - **Write:** none
- **Mapper:** `mappers.py` present with placeholder outbound mapping.

### Confluence
- **Connector IDs:** `confluence`
- **Sync directions:** inbound
- **REST operations:**
  - **Read:** spaces, pages
  - **Write:** pages

### Google Calendar
- **Connector IDs:** `google_calendar`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** events, calendars
  - **Write:** events

### Google Drive
- **Connector IDs:** `google_drive`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** files, folders
  - **Write:** files

### IoT
- **Connector IDs:** `iot`
- **Sync directions:** inbound, outbound
- **REST operations:**
  - **Read:** sensor data, devices
  - **Write:** sensor data (ingest), commands

### Jira
- **Connector IDs:** `jira`
- **Sync directions:** inbound
- **REST operations:**
  - **Read:** projects, issues
  - **Write:** issues (create/update)
- **MCP fallback:** list/create/update for issues when MCP tool map permits.

### LogicGate
- **Connector IDs:** `logicgate`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** workflows, records
  - **Write:** records

### Monday.com
- **Connector IDs:** `monday`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** boards, items
  - **Write:** items

### Microsoft Project Server
- **Connector IDs:** `ms_project_server`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** projects, tasks
  - **Write:** tasks

### Microsoft 365
- **Connector IDs:** `m365`
- **Sync directions:** inbound
- **REST operations:**
  - **Read:** teams, channels, messages, events, mail, sites, drives, lists, planner plans, planner tasks, drive items, Power BI reports/dashboards, Viva Learning providers
  - **Write:** none

### NetSuite
- **Connector IDs:** `netsuite`
- **Sync directions:** inbound
- **REST operations:**
  - **Read:** projects, customers
  - **Write:** none

### Azure Notification Hubs
- **Connector IDs:** `notification_hubs`
- **Sync directions:** outbound
- **REST operations:**
  - **Read:** notifications
  - **Write:** notifications (send)

### Oracle ERP Cloud
- **Connector IDs:** `oracle`
- **Sync directions:** inbound
- **REST operations:**
  - **Read:** projects, invoices
  - **Write:** none

### Outlook
- **Connector IDs:** `outlook`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** events, calendar view, calendars
  - **Write:** events

### Planview
- **Connector IDs:** `planview`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** projects (schema also lists portfolios, but read only supports projects)
  - **Write:** none
- **Mapper:** `mappers.py` present with placeholder outbound mapping.

### Salesforce
- **Connector IDs:** `salesforce`
- **Sync directions:** inbound
- **REST operations:**
  - **Read:** projects (from `run_sync` in `main.py`)
  - **Write:** none

### SAP
- **Connector IDs:** `sap`
- **Sync directions:** inbound
- **REST operations:**
  - **Read:** projects, costs
  - **Write:** none
- **Mapper:** `mappers.py` present with placeholder outbound mapping.
- **MCP fallback:** uses operation router when MCP tool map is configured.

### SAP SuccessFactors
- **Connector IDs:** `sap_successfactors`
- **Sync directions:** inbound
- **REST operations:**
  - **Read:** users, jobs
  - **Write:** none

### ServiceNow GRC
- **Connector IDs:** `servicenow`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** profiles, risks
  - **Write:** risks

### SharePoint
- **Connector IDs:** `sharepoint`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** lists, documents
  - **Write:** documents

### Slack
- **Connector IDs:** `slack`
- **Sync directions:** inbound, outbound, bidirectional
- **REST operations:**
  - **Read:** channels, users
  - **Write:** messages (post)

### Smartsheet
- **Connector IDs:** `smartsheet`
- **Sync directions:** inbound, bidirectional
- **REST operations:**
  - **Read:** sheets, workspaces
  - **Write:** sheets

### Microsoft Teams
- **Connector IDs:** `teams`
- **Sync directions:** outbound, bidirectional
- **REST operations:**
  - **Read:** teams, channels, messages
  - **Write:** messages (post)

### Twilio
- **Connector IDs:** `twilio`
- **Sync directions:** outbound, bidirectional
- **REST operations:**
  - **Read:** messages
  - **Write:** messages (send)

### Workday
- **Connector IDs:** `workday`
- **Sync directions:** inbound
- **REST operations:**
  - **Read:** workers, positions
  - **Write:** none
- **MCP fallback:** uses operation router when MCP tool map is configured.

### Zoom
- **Connector IDs:** `zoom`
- **Sync directions:** inbound, outbound
- **REST operations:**
  - **Read:** meetings, webinars
  - **Write:** none

## MCP server availability + tool coverage

### MCP connector manifests (packages in `integrations/connectors/*_mcp`)
- **Jira MCP (`jira_mcp`)**: tools for listing projects/work items and upserting work items.
- **Slack MCP (`slack_mcp`)**: tools for listing channels/users and posting messages.
- **Teams MCP (`teams_mcp`)**: tools for listing teams/channels and posting messages.
- **SAP MCP (`sap_mcp`)**: tools for listing invoices, goods receipts, purchase orders, suppliers.
- **Workday MCP (`workday_mcp`)**: tools for listing workers, job profiles, positions, organizations.

### MCP connector definitions in SDK registry
- **Planview MCP (`planview_mcp`)**: declared with supported operations `list` + `create`.
- **Clarity MCP (`clarity_mcp`)**: declared with supported operations `list` + `create`.

## MCP tools vs REST operations (coverage matrix)

| System | REST operations today | MCP tool coverage | Coverage gaps / notes |
| --- | --- | --- | --- |
| **Planview** | Read projects only. | SDK registry advertises `list` + `create`. | Connector implementation is read-only; MCP mapping only supports list. No create support in REST connector. |
| **Clarity** | Read projects only. | SDK registry advertises `list` + `create`. | No MCP package under `integrations/connectors/clarity_mcp`; REST connector is read-only (no create). |
| **Jira** | Read projects & issues; write issues (create/update). | MCP tools: list projects, list work items, upsert work item. | MCP lacks delete and explicit project write operations; REST has richer issue update logic + transitions. |
| **Slack** | Read channels/users; write messages (post). | MCP tools: list channels, list users, post message. | Parity for current REST operations; no message-history read in either connector. |
| **Teams** | Read teams/channels/messages; write messages. | MCP tools: list teams, list channels, post message. | MCP lacks list/read messages tool; REST can read messages via Graph endpoint. |
| **SAP** | Read projects & costs. | MCP tools: list invoices, goods receipts, purchase orders, suppliers. | Tool coverage does **not** overlap current REST resource types (projects/costs vs finance/procurement data). |
| **Workday** | Read workers & positions. | MCP tools: list workers, job profiles, positions, organizations. | MCP has job profiles/organizations not present in REST connector; REST lacks those resources. |
