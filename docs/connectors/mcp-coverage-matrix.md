# MCP Coverage Matrix (SAP + Workday)

## Purpose

This matrix shows which SAP and Workday operations are currently backed by MCP tools versus REST connector coverage. It highlights gaps in MCP coverage, plus where REST read support exists and where write operations would need REST fallbacks.

## SAP

**Sources:**
- MCP tool map: `integrations/connectors/sap_mcp/manifest.yaml`
- REST connector mappings: `integrations/connectors/sap/manifest.yaml`

| Operation / entity | MCP tool (tool_map key → tool) | MCP read support | REST read support | Write support & fallback | Gaps / notes |
| --- | --- | --- | --- | --- | --- |
| Invoices | `list_invoices` → `sap.listInvoices` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Goods receipts | `list_goods_receipts` → `sap.listGoodsReceipts` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Purchase orders | `list_purchase_orders` → `sap.listPurchaseOrders` | ✅ | ✅ (`purchase_order` mapping) | ❌ No write tool; REST write not defined | REST can read via canonical sync; MCP has tool. |
| Suppliers | `list_suppliers` → `sap.listSuppliers` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Projects (canonical sync) | — | ❌ | ✅ (`project` mapping) | ❌ No MCP write tool; REST write not defined | REST-only today; add MCP tool to close gap. |

## Workday

**Sources:**
- MCP tool map: `integrations/connectors/workday_mcp/manifest.yaml`
- REST connector mappings: `integrations/connectors/workday/manifest.yaml`

| Operation / entity | MCP tool (tool_map key → tool) | MCP read support | REST read support | Write support & fallback | Gaps / notes |
| --- | --- | --- | --- | --- | --- |
| Workers | `list_workers` → `workday.listWorkers` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Job profiles | `list_job_profiles` → `workday.listJobProfiles` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Positions | `list_positions` → `workday.listPositions` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Organizations | `list_organizations` → `workday.listOrganizations` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Projects (canonical sync) | — | ❌ | ✅ (`project` mapping) | ❌ No MCP write tool; REST write not defined | REST-only today; add MCP tool to close gap. |
| Resources (canonical sync) | — | ❌ | ✅ (`resource` mapping) | ❌ No MCP write tool; REST write not defined | REST-only today; add MCP tool to close gap. |

## Write-operation fallbacks

- MCP routing is operation-aware: if `prefer_mcp` is enabled and a tool is mapped, MCP is used; otherwise it falls back to REST. Missing MCP tools (or disabled MCP ops) route to REST automatically in `OperationRouter`.
- The MCP client expects CRUD-style mappings via `mcp_tool_map` (e.g., `create_record`, `update_record`), so write support requires explicit tool entries in the map.

## Extending MCP coverage

1. **Add or expand MCP tool mappings**
   - Update the MCP manifest `mcp.tool_map` for the connector (e.g., `integrations/connectors/sap_mcp/manifest.yaml`, `integrations/connectors/workday_mcp/manifest.yaml`).
   - If you’re wiring MCP support into connector configs, populate `mcp_tool_map` in `ConnectorConfig` (this is the authoritative map the MCP client uses).

2. **Decide MCP vs REST routing**
   - Enable MCP routing using `prefer_mcp`, `mcp_enabled_operations`, or `mcp_disabled_operations` in the connector config and verify how `OperationRouter` resolves the operation.

3. **Add REST fallbacks for new write operations (if needed)**
   - If MCP tools for writes are not available, implement REST endpoints in the relevant connector or ensure the REST connector supports the write operation so the router can fall back safely.
