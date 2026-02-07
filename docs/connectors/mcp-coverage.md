# MCP Coverage Classification (Task 1 Inventory)

This reference classifies each connector from the Task 1 inventory as **MCP-ready**, **hybrid**, or **REST-only**, and calls out which operations are MCP-covered versus REST-only.

**Legend**
- **MCP-ready**: MCP tools cover all currently documented operations for the connector.
- **Hybrid**: MCP tools exist for a subset of operations; remaining operations require REST.
- **REST-only**: no MCP tools are documented; all operations rely on REST.

| Connector | Classification | MCP-covered operations | REST-only operations / notes |
| --- | --- | --- | --- |
| ADP | REST-only | — | Read: workers, payroll. |
| Archer (RSA Archer) | REST-only | — | Read: risks. |
| Asana | REST-only | — | Read: projects, tasks. Write: tasks. |
| Azure DevOps | REST-only | — | Read: projects, work items. Write: work items. |
| Azure Communication Services | REST-only | — | Read: sms, email. Write: sms (send), email (send). |
| Clarity PPM | REST-only | — | Read: projects. |
| Confluence | REST-only | — | Read: spaces, pages. Write: pages. |
| Google Calendar | REST-only | — | Read: events, calendars. Write: events. |
| Google Drive | REST-only | — | Read: files, folders. Write: files. |
| IoT | REST-only | — | Read: sensor data, devices. Write: sensor data (ingest), commands. |
| Jira | MCP-ready | Read: projects, issues. Write: issues (create/update). | — |
| LogicGate | REST-only | — | Read: workflows, records. Write: records. |
| Monday.com | REST-only | — | Read: boards, items. Write: items. |
| Microsoft Project Server | REST-only | — | Read: projects, tasks. Write: tasks. |
| Microsoft 365 | REST-only | — | Read: teams, channels, messages, events, mail, sites, drives, lists, planner plans, planner tasks, drive items, Power BI reports/dashboards, Viva Learning providers. |
| NetSuite | REST-only | — | Read: projects, customers. |
| Azure Notification Hubs | REST-only | — | Read: notifications. Write: notifications (send). |
| Oracle ERP Cloud | REST-only | — | Read: projects, invoices. |
| Outlook | REST-only | — | Read: events, calendar view, calendars. Write: events. |
| Planview | REST-only | — | Read: projects. |
| Salesforce | REST-only | — | Read: projects. |
| SAP | Hybrid | Read (MCP): invoices, goods receipts, purchase orders, suppliers. | Read (REST-only): projects, costs. No write operations documented. |
| SAP SuccessFactors | REST-only | — | Read: users, jobs. |
| ServiceNow GRC | REST-only | — | Read: profiles, risks. Write: risks. |
| SharePoint | REST-only | — | Read: lists, documents. Write: documents. |
| Slack | MCP-ready | Read: channels, users. Write: messages (post). | — |
| Smartsheet | REST-only | — | Read: sheets, workspaces. Write: sheets. |
| Microsoft Teams | Hybrid | Read (MCP): teams, channels. Write (MCP): messages (post). | Read (REST-only): messages. |
| Twilio | REST-only | — | Read: messages. Write: messages (send). |
| Workday | MCP-ready | Read (MCP): workers, positions (plus MCP-only: job profiles, organizations). | — |
| Zoom | REST-only | — | Read: meetings, webinars. |
